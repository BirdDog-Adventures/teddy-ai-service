"""
Snowflake Connector for accessing SSURGO soil data and Regrid parcel data
"""
import snowflake.connector
from typing import List, Dict, Any, Optional
import logging
import pandas as pd
from contextlib import contextmanager
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from api.core.config import settings

logger = logging.getLogger(__name__)


class SnowflakeConnector:
    def __init__(self):
        self.account = settings.SNOWFLAKE_ACCOUNT
        self.user = settings.SNOWFLAKE_USER
        self.password = settings.SNOWFLAKE_PASSWORD
        self.private_key_path = settings.SNOWFLAKE_PRIVATE_KEY_PATH
        self.database = settings.SNOWFLAKE_DATABASE
        self.schema = settings.SNOWFLAKE_SCHEMA
        self.warehouse = settings.SNOWFLAKE_WAREHOUSE
        self.role = settings.SNOWFLAKE_ROLE
        self._private_key = None
        
        # Load private key if path is provided
        if self.private_key_path and not self.password:
            self._load_private_key()
    
    def _load_private_key(self):
        """Load private key from file"""
        try:
            with open(self.private_key_path, "rb") as key_file:
                private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None,
                    backend=default_backend()
                )
                self._private_key = private_key.private_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
        except Exception as e:
            logger.error(f"Error loading private key: {str(e)}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get Snowflake connection context manager"""
        conn = None
        try:
            # Build connection parameters
            conn_params = {
                "account": self.account,
                "user": self.user,
                "database": self.database,
                "schema": self.schema,
                "warehouse": self.warehouse,
                "role": self.role
            }
            
            # Use private key if available, otherwise use password
            if self._private_key:
                conn_params["private_key"] = self._private_key
            elif self.password:
                conn_params["password"] = self.password
            else:
                raise ValueError("Either password or private key must be provided")
            
            conn = snowflake.connector.connect(**conn_params)
            yield conn
        except Exception as e:
            logger.error(f"Error connecting to Snowflake: {str(e)}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()
    
    async def get_property_boundaries(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Get property boundaries from Regrid data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for property boundaries
                query = """
                SELECT 
                    property_id,
                    parcel_id,
                    owner_name,
                    address,
                    city,
                    state,
                    zip_code,
                    acreage,
                    ST_AsGeoJSON(geometry) as geometry_json,
                    assessed_value,
                    land_use_code
                FROM REGRID_PARCELS
                WHERE property_id = %s
                """
                
                cursor.execute(query, (property_id,))
                result = cursor.fetchone()
                
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, result))
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting property boundaries: {str(e)}", exc_info=True)
            raise
    
    async def get_soil_data(self, property_id: str) -> List[Dict[str, Any]]:
        """Get SSURGO soil data for a property"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for soil data
                query = """
                WITH property_bounds AS (
                    SELECT geometry
                    FROM REGRID_PARCELS
                    WHERE property_id = %s
                )
                SELECT 
                    m.MUKEY,
                    m.MUSYM,
                    m.MUNAME,
                    m.MUACRES,
                    c.COMPNAME,
                    c.COMPPCT_R,
                    c.DRAINAGECL,
                    c.HYDGRP,
                    c.TAXORDER,
                    c.NIRRCAPCL,
                    c.IRRCAPCL,
                    ch.HZDEPT_R,
                    ch.HZDEPB_R,
                    ch.SANDTOTAL_R,
                    ch.SILTTOTAL_R,
                    ch.CLAYTOTAL_R,
                    ch.OM_R,
                    ch.PH1TO1H2O_R,
                    ch.CEC7_R,
                    ch.AWC_R
                FROM SSURGO_MAPUNIT m
                JOIN SSURGO_COMPONENT c ON m.MUKEY = c.MUKEY
                JOIN SSURGO_CHORIZON ch ON c.COKEY = ch.COKEY
                JOIN property_bounds pb ON ST_Intersects(m.GEOMETRY_WKT, pb.geometry)
                WHERE c.MAJCOMPFLAG = 'Yes'
                ORDER BY m.MUKEY, c.COMPPCT_R DESC, ch.HZDEPT_R
                """
                
                cursor.execute(query, (property_id,))
                results = cursor.fetchall()
                
                if results:
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in results]
                
                return []
                
        except Exception as e:
            logger.error(f"Error getting soil data: {str(e)}", exc_info=True)
            raise
    
    async def search_properties_by_criteria(
        self,
        filters: Dict[str, Any],
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search properties by various criteria"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic query based on filters
                where_clauses = []
                params = []
                
                if filters.get("min_acreage"):
                    where_clauses.append("acreage >= %s")
                    params.append(filters["min_acreage"])
                
                if filters.get("max_acreage"):
                    where_clauses.append("acreage <= %s")
                    params.append(filters["max_acreage"])
                
                if filters.get("county"):
                    where_clauses.append("LOWER(county) = LOWER(%s)")
                    params.append(filters["county"])
                
                if filters.get("state"):
                    where_clauses.append("LOWER(state) = LOWER(%s)")
                    params.append(filters["state"])
                
                where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                query = f"""
                SELECT 
                    property_id,
                    parcel_id,
                    owner_name,
                    address,
                    city,
                    state,
                    county,
                    zip_code,
                    acreage,
                    assessed_value,
                    land_use_code,
                    ST_Y(ST_Centroid(geometry)) as latitude,
                    ST_X(ST_Centroid(geometry)) as longitude
                FROM REGRID_PARCELS
                WHERE {where_clause}
                LIMIT %s
                """
                
                params.append(limit)
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                if results:
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in results]
                
                return []
                
        except Exception as e:
            logger.error(f"Error searching properties: {str(e)}", exc_info=True)
            raise
    
    async def get_crop_history(self, property_id: str, years: int = 5) -> List[Dict[str, Any]]:
        """Get crop history for a property"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for crop history (assuming CDL data is loaded)
                query = """
                SELECT 
                    year,
                    crop_type,
                    acreage,
                    confidence_score
                FROM CROP_DATA_LAYER
                WHERE property_id = %s
                    AND year >= YEAR(CURRENT_DATE) - %s
                ORDER BY year DESC
                """
                
                cursor.execute(query, (property_id, years))
                results = cursor.fetchall()
                
                if results:
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in results]
                
                return []
                
        except Exception as e:
            logger.error(f"Error getting crop history: {str(e)}", exc_info=True)
            raise
    
    async def get_nearby_properties(
        self,
        latitude: float,
        longitude: float,
        radius_miles: float,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get properties within a radius of a location"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Convert miles to meters for ST_DWithin
                radius_meters = radius_miles * 1609.34
                
                query = """
                SELECT 
                    property_id,
                    parcel_id,
                    address,
                    city,
                    state,
                    acreage,
                    ST_Distance(
                        geometry,
                        ST_MakePoint(%s, %s)
                    ) / 1609.34 as distance_miles
                FROM REGRID_PARCELS
                WHERE ST_DWithin(
                    geometry,
                    ST_MakePoint(%s, %s),
                    %s
                )
                ORDER BY distance_miles
                LIMIT %s
                """
                
                cursor.execute(query, (
                    longitude, latitude,
                    longitude, latitude,
                    radius_meters,
                    limit
                ))
                results = cursor.fetchall()
                
                if results:
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in results]
                
                return []
                
        except Exception as e:
            logger.error(f"Error getting nearby properties: {str(e)}", exc_info=True)
            raise
