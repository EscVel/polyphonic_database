import sys
import json
import os
import mysql.connector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

db_config = {
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'host': os.environ.get('DB_HOST'),
    'database': os.environ.get('DB_DATABASE')
}

def get_lineage(childid):
    """Query the audio lineage recursively for a given audio file."""
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # The Recursive Query (Same as we ran in Workbench)
        query = """
            WITH RECURSIVE AudioLineage AS (
                SELECT parentid, childid, transformationtype, 1 as generation_level
                FROM derivations 
                WHERE childid = %s
                
                UNION ALL
                
                SELECT d.parentid, d.childid, d.transformationtype, al.generation_level + 1
                FROM derivations d
                INNER JOIN AudioLineage al ON d.childid = al.parentid
            )
            SELECT 
                al.generation_level,
                al.parentid,
                p.AudioName as parent_name,
                al.childid,
                c.AudioName as child_name,
                al.transformationtype
            FROM AudioLineage al
            JOIN Audio p ON al.parentid = p.AudioId
            JOIN Audio c ON al.childid = c.AudioId
            ORDER BY generation_level;
        """

        cursor.execute(query, (childid,))
        results = cursor.fetchall()

        return {
            "status": "success",
            "lineage": results,
            "count": len(results)
        }

    except mysql.connector.Error as err:
        return {"status": "error", "message": str(err)}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "No audio ID provided"}))
        sys.exit(1)

    try:
        childid = int(sys.argv[1])
        result = get_lineage(childid)
        print(json.dumps(result))
    except ValueError:
        print(json.dumps({"status": "error", "message": "Invalid audio ID (must be integer)"}))
        sys.exit(1)
