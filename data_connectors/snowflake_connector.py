"""
Snowflake Connector for accessing SSURGO soil data and Parcel data
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
        """Get property boundaries from PARCEL_PROFILE table"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for property boundaries using actual schema
                query = """
                SELECT 
                    PARCEL_ID,
                    ADDRESS,
                    CITY,
                    STATE_CODE,
                    ZIP_CODE,
                    ACRES,
                    OWNER_NAME,
                    TOTAL_VALUE,
                    LAND_VALUE,
                    IMPROVEMENT_VALUE,
                    USECODE,
                    USEDESC,
                    ZONING,
                    ZONING_DESCRIPTION,
                    COUNTY_ID,
                    PARCEL_GEOJSON,
                    LATITUDE,
                    LONGITUDE
                FROM PARCEL_PROFILE
                WHERE PARCEL_ID = %s
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
        """Get soil data for a property from SOIL_PROFILE table"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for soil data using correct schema columns
                query = """
                SELECT 
                    sp.PARCEL_ID,
                    sp.MUKEY,
                    sp.MAP_UNIT_SYMBOL,
                    sp.COMPONENT_KEY,
                    sp.COMPONENT_PERCENTAGE,
                    sp.SOIL_SERIES,
                    sp.SOIL_TYPE,
                    sp.FERTILITY_CLASS,
                    sp.ORGANIC_MATTER_PCT,
                    sp.PH_LEVEL,
                    sp.CATION_EXCHANGE_CAPACITY,
                    sp.DRAINAGE_CLASS,
                    sp.HYDROLOGIC_GROUP,
                    sp.SLOPE_PERCENT,
                    sp.AVAILABLE_WATER_CAPACITY,
                    sp.NITROGEN_PPM,
                    sp.PHOSPHORUS_PPM,
                    sp.POTASSIUM_PPM,
                    sp.TAXONOMIC_CLASS,
                    sp.AGRICULTURAL_CAPABILITY,
                    sp.SAMPLING_DEPTH_CM,
                    sp.CONFIDENCE_SCORE,
                    sp.MATCH_QUALITY,
                    sp.DISTANCE_MILES,
                    pp.ADDRESS,
                    pp.CITY,
                    pp.STATE_CODE,
                    pp.ACRES,
                    pp.COUNTY_ID
                FROM SOIL_PROFILE sp
                JOIN PARCEL_PROFILE pp ON sp.PARCEL_ID = pp.PARCEL_ID
                WHERE sp.PARCEL_ID = %s
                ORDER BY sp.COMPONENT_PERCENTAGE DESC
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
                    where_clauses.append("ACRES >= %s")
                    params.append(filters["min_acreage"])
                
                if filters.get("max_acreage"):
                    where_clauses.append("ACRES <= %s")
                    params.append(filters["max_acreage"])
                
                if filters.get("county"):
                    where_clauses.append("LOWER(COUNTY_ID) = LOWER(%s)")
                    params.append(filters["county"])
                
                if filters.get("state"):
                    where_clauses.append("LOWER(STATE_CODE) = LOWER(%s)")
                    params.append(filters["state"])
                
                where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                query = f"""
                SELECT 
                    PARCEL_ID,
                    ADDRESS,
                    CITY,
                    STATE_CODE,
                    COUNTY_ID,
                    ZIP_CODE,
                    ACRES,
                    OWNER_NAME,
                    TOTAL_VALUE,
                    USECODE,
                    USEDESC,
                    LATITUDE,
                    LONGITUDE
                FROM PARCEL_PROFILE
                WHERE {where_clause}
                    AND ACRES IS NOT NULL
                    AND LATITUDE IS NOT NULL
                    AND LONGITUDE IS NOT NULL
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
        """Get crop history for a property from CROP_HISTORY table"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for crop history using correct schema
                query = """
                SELECT 
                    HISTORY_ID,
                    PARCEL_ID,
                    CROP_YEAR,
                    CROP_TYPE,
                    ROTATION_SEQUENCE,
                    CROP_GEOJSON,
                    COUNTY_ID,
                    STATE_CODE,
                    CREATED_AT,
                    UPDATED_AT
                FROM CROP_HISTORY
                WHERE PARCEL_ID = %s
                    AND CROP_YEAR >= YEAR(CURRENT_DATE) - %s
                ORDER BY CROP_YEAR DESC, ROTATION_SEQUENCE ASC
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
    
    async def get_comprehensive_analysis(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive parcel analysis from COMPREHENSIVE_PARCEL_CDL_ANALYSIS table"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for comprehensive analysis
                query = """
                SELECT 
                    PARCEL_ID,
                    PARCEL_ACRES,
                    COUNTY_ID,
                    STATE_CODE,
                    ADDRESS,
                    OWNER_NAME,
                    USECODE,
                    USEDESC,
                    ZONING,
                    ZONING_DESCRIPTION,
                    HOMESTEAD_EXEMPTION,
                    TOTAL_VALUE,
                    LAND_VALUE,
                    IMPROVEMENT_VALUE,
                    TAXAMT,
                    SALEPRICE,
                    SALEDATE,
                    LAND_COVER_SUMMARY,
                    DOMINANT_COVER_TYPE,
                    DOMINANT_COVER_PERCENTAGE,
                    TOTAL_COVER_TYPES,
                    AGRICULTURAL_PERCENTAGE,
                    FOREST_PERCENTAGE,
                    DEVELOPED_PERCENTAGE,
                    CROP_SUMMARY,
                    DOMINANT_CROP,
                    TOTAL_AGRICULTURAL_CROPS,
                    AGRICULTURAL_CLASSIFICATION,
                    SECTION_180_POTENTIAL,
                    TAX_EXEMPTION_ANALYSIS,
                    VALUATION_FLAG,
                    INVESTMENT_OPPORTUNITY_FLAG
                FROM COMPREHENSIVE_PARCEL_CDL_ANALYSIS
                WHERE PARCEL_ID = %s
                """
                
                cursor.execute(query, (property_id,))
                result = cursor.fetchone()
                
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, result))
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting comprehensive analysis: {str(e)}", exc_info=True)
            raise
    
    async def get_climate_data(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Get climate data for a property from CLIMATE_DATA table"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for climate data
                query = """
                SELECT 
                    CLIMATE_ID,
                    PARCEL_ID,
                    COUNTY_ID,
                    STATE_CODE,
                    DATA_YEAR,
                    ANNUAL_PRECIPITATION_INCHES,
                    ANNUAL_PRECIPITATION_MM,
                    ANNUAL_SNOWFALL_INCHES,
                    GROWING_DEGREE_DAYS,
                    AVG_TEMPERATURE_F,
                    MAX_TEMPERATURE_F,
                    MIN_TEMPERATURE_F,
                    CLIMATE_CLASSIFICATION,
                    WEATHER_STATION_NAME,
                    STATION_DISTANCE_MILES,
                    YEARS_OF_DATA,
                    DATA_PERIOD,
                    IS_MULTI_YEAR_AVERAGE
                FROM CLIMATE_DATA
                WHERE PARCEL_ID = %s
                ORDER BY DATA_YEAR DESC
                LIMIT 1
                """
                
                cursor.execute(query, (property_id,))
                result = cursor.fetchone()
                
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, result))
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting climate data: {str(e)}", exc_info=True)
            raise
    
    async def get_section_180_estimates(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Get Section 180 tax deduction estimates for a property"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for Section 180 estimates
                query = """
                SELECT 
                    ESTIMATE_ID,
                    PARCEL_ID,
                    ESTIMATE_DATE,
                    TOTAL_DEDUCTION,
                    NITROGEN_VALUE,
                    PHOSPHORUS_VALUE,
                    POTASSIUM_VALUE,
                    CONFIDENCE_SCORE,
                    METHODOLOGY,
                    NOTES
                FROM SECTION_180_ESTIMATES
                WHERE PARCEL_ID = %s
                ORDER BY ESTIMATE_DATE DESC
                LIMIT 1
                """
                
                cursor.execute(query, (property_id,))
                result = cursor.fetchone()
                
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, result))
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting Section 180 estimates: {str(e)}", exc_info=True)
            raise
    
    async def get_topography_data(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Get topography data for a property"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for topography data
                query = """
                SELECT 
                    TOPO_ID,
                    PARCEL_ID,
                    MEAN_ELEVATION_FT,
                    MIN_ELEVATION_FT,
                    MAX_ELEVATION_FT,
                    ELEVATION_VARIANCE_FT,
                    SLOPE_PERCENT,
                    TERRAIN_ANALYSIS,
                    RESOLUTION,
                    COLLECTION_METHOD,
                    COLLECTION_DATE
                FROM TOPOGRAPHY
                WHERE PARCEL_ID = %s
                ORDER BY COLLECTION_DATE DESC
                LIMIT 1
                """
                
                cursor.execute(query, (property_id,))
                result = cursor.fetchone()
                
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, result))
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting topography data: {str(e)}", exc_info=True)
            raise
