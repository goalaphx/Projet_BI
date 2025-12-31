import os
import sys
import random
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, size, split, when, lit, explode, year, current_timestamp
from pyspark.sql.types import StringType, IntegerType, StructType, StructField, DoubleType, ArrayType

# --- 1. CRITICAL FIX FOR PYTHON 3.11 ON WINDOWS ---
# This forces Spark to use the currently running Python executable
os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

# --- 2. ENVIRONMENT CONFIGURATION ---
# (Keep your existing path config here)
os.environ['JAVA_HOME'] = r"C:\Program Files\Java\jdk-11"
os.environ['HADOOP_HOME'] = r"C:\hadoop"
os.environ['PATH'] = os.environ['JAVA_HOME'] + "\\bin;" + \
                     os.environ['HADOOP_HOME'] + "\\bin;" + \
                     os.environ['PATH']
# (Keep your existing Path setup)

# --- UDFS FOR DATA ENRICHMENT (Simulating the BI Dimensions) ---
# We use UDFs (User Defined Functions) to generate the missing data "permanently"

def simulate_quartile():
    return random.choices(["Q1", "Q2", "Q3", "Q4"], weights=[20, 30, 30, 20])[0]

def simulate_country():
    countries = ["USA", "China", "India", "UK", "France", "Germany", "Morocco", "Canada"]
    weights = [20, 18, 15, 10, 8, 8, 5, 5]
    return random.choices(countries, weights=weights)[0]

def simulate_impact_score():
    return round(random.uniform(0.5, 15.0), 2)

def extract_keywords(title):
    # Simple logic: extract interesting words from title if keywords missing
    stopwords = ["the", "for", "and", "with", "based", "using", "approach"]
    words = title.lower().replace("-", " ").split()
    return [w.capitalize() for w in words if len(w) > 4 and w not in stopwords]

# Register UDFs
udf_quartile = udf(simulate_quartile, StringType())
udf_country = udf(simulate_country, StringType())
udf_impact = udf(simulate_impact_score, DoubleType())
udf_keywords = udf(extract_keywords, ArrayType(StringType()))

# --- MAIN PIPELINE ---
spark = SparkSession.builder \
    .appName("BlockchainDWBuilder") \
    .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:10.2.0") \
    .config("spark.mongodb.read.connection.uri", "mongodb://localhost:27017/aci.articles") \
    .config("spark.mongodb.write.connection.uri", "mongodb://localhost:27017/aci.fact_publications") \
    .getOrCreate()

print(">>> READING RAW DATA...")
raw_df = spark.read.format("mongodb").load()

# --- 1. CLEANING & DIMENSION BUILDER ---
# Clean Author string "Name1;\nName2" -> Array ["Name1", "Name2"]
df_clean = raw_df.withColumn("authors_clean", split(col("authors"), ";\\\\n|;"))

# --- 2. FACT TABLE CONSTRUCTION (F_Publications) ---
# We add the measures: nb_authors, citations (simulated), impact_score
# We add the dimensions: time, geo, journal
df_dw = df_clean.withColumn("nb_authors", size(col("authors_clean"))) \
    .withColumn("quartile", udf_quartile()) \
    .withColumn("country", udf_country()) \
    .withColumn("impact_score", udf_impact()) \
    .withColumn("citations", (col("impact_score") * 10).cast(IntegerType())) \
    .withColumn("generated_keywords", udf_keywords(col("title"))) \
    .withColumn("etl_timestamp", current_timestamp())

# Drop raw columns we don't need
df_final = df_dw.drop("authors", "_id")

print(">>> TRANSFORMED DATA SAMPLE:")
df_final.select("title", "quartile", "country", "nb_authors").show(5)

# --- 3. LOAD TO DATA WAREHOUSE (MongoDB) ---
print(">>> WRITING TO FACT TABLE (aci.fact_publications)...")
df_final.write.format("mongodb").mode("overwrite").save()

print("✅ ETL COMPLETE. Data Warehouse ready.")
spark.stop()