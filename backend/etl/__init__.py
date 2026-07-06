# Bharat Tech Atlas — ETL Pipeline Module
# Extract data from DPIIT, Tracxn, Crunchbase APIs
# Transform: clean, normalize categories, geocode addresses
# Load: into SQLite with spatial indexing


def get_pipeline():
    from .pipeline import ETLPipeline
    return ETLPipeline


def get_extractor():
    from .extract import ETLExtractor
    return ETLExtractor
