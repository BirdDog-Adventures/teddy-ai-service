#!/usr/bin/env python3
"""
Script to list available tables in Snowflake database
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_connectors.snowflake_connector import SnowflakeConnector
import asyncio

async def list_tables():
    """List all tables in the Snowflake database"""
    connector = SnowflakeConnector()
    
    try:
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            
            # List all tables in the current schema
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            print("Available tables in Snowflake:")
            print("=" * 50)
            
            if tables:
                for table in tables:
                    # Table info: [created_on, name, database_name, schema_name, kind, comment, cluster_by, rows, bytes, owner, retention_time, automatic_clustering, change_tracking, search_optimization, search_optimization_progress, search_optimization_bytes, is_external, enable_schema_evolution, owner_role_type, is_event, budget]
                    table_name = table[1]  # name is at index 1
                    database_name = table[2]  # database_name is at index 2
                    schema_name = table[3]  # schema_name is at index 3
                    rows = table[7] if len(table) > 7 else "Unknown"  # rows is at index 7
                    
                    print(f"  {database_name}.{schema_name}.{table_name} (rows: {rows})")
            else:
                print("  No tables found in the current schema")
                
            # Also try to list tables with a different query
            print("\nAlternative table listing:")
            print("=" * 50)
            
            cursor.execute("""
                SELECT table_name, table_schema, table_catalog 
                FROM information_schema.tables 
                WHERE table_schema = CURRENT_SCHEMA()
                ORDER BY table_name
            """)
            
            info_tables = cursor.fetchall()
            for table in info_tables:
                print(f"  {table[2]}.{table[1]}.{table[0]}")
                
    except Exception as e:
        print(f"Error connecting to Snowflake: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(list_tables())
