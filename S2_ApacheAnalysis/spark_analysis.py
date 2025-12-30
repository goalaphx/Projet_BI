from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count

# --- 1. INITIALIZE SPARK (STABLE 3.4 SETUP) ---
# We use Connector 10.2.0 which is perfectly compatible with Spark 3.4
spark = SparkSession.builder \
    .appName("BlockchainAnalysis") \
    .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:10.2.0") \
    .config("spark.mongodb.read.connection.uri", "mongodb://mongodb:27017/aci.articles") \
    .config("spark.mongodb.write.connection.uri", "mongodb://mongodb:27017/aci.articles") \
    .getOrCreate()

print("\n" + "="*50)
print("--- SPARK 3.4 ANALYSIS RUNNING ---")

# --- 2. LOAD DATA ---
try:
    df = spark.read.format("mongodb").load()
    print(f"✅ Success! Loaded {df.count()} documents.")
except Exception as e:
    print(f"❌ Error loading data: {e}")
    spark.stop()
    exit()

# --- 3. SCHEMA ---
print("\n--- SCHEMA ---")
df.printSchema()

# --- 4. ANALYSIS: PUBLICATIONS PER YEAR ---
print("\n--- PUBLICATIONS PER YEAR ---")
if "date_pub" in df.columns:
    # Filter out bad dates and count
    df.filter(col("date_pub") != "Unknown Date") \
      .groupBy("date_pub") \
      .agg(count("*").alias("count")) \
      .sort("date_pub", ascending=True) \
      .show(30)
else:
    print("Warning: 'date_pub' column not found.")

print("="*50 + "\n")
spark.stop()