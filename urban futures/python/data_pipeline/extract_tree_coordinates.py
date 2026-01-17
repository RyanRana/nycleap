#!/usr/bin/env python3
"""
Extract just the coordinates from street trees census for frontend display.
Creates a lightweight JSON file with only alive tree coordinates.
"""

import pandas as pd
import json
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
CACHE_DIR = BASE_DIR / "data" / "cache"
OUTPUT_DIR = BASE_DIR / "frontend" / "public" / "data" / "processed"

def extract_tree_coordinates():
    """Extract alive tree coordinates to lightweight JSON."""
    print("Loading street trees census data...")
    trees_path = CACHE_DIR / "street_trees_2015.csv"
    
    # Read only needed columns
    df = pd.read_csv(
        trees_path,
        usecols=['latitude', 'longitude', 'status'],
        low_memory=False
    )
    
    print(f"  Loaded {len(df):,} total trees")
    
    # Filter to alive trees only
    df = df[df['status'] == 'Alive'].copy()
    print(f"  Filtered to {len(df):,} alive trees")
    
    # Remove any NaN coordinates
    df = df[df['latitude'].notna() & df['longitude'].notna()].copy()
    print(f"  After removing NaN: {len(df):,} trees")
    
    # Convert to list of coordinate dicts
    coordinates = [
        {
            'latitude': float(row['latitude']),
            'longitude': float(row['longitude'])
        }
        for _, row in df.iterrows()
    ]
    
    # Create output data
    output_data = {
        'metadata': {
            'source': '2015 Street Tree Census',
            'total_trees': len(coordinates),
            'status_filter': 'Alive',
            'description': 'Existing street trees in NYC'
        },
        'coordinates': coordinates
    }
    
    # Save to JSON
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "existing_trees_coordinates.json"
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\n✅ Saved {len(coordinates):,} tree coordinates")
    print(f"   File: {output_path}")
    print(f"   Size: {file_size_mb:.1f} MB")

if __name__ == '__main__':
    extract_tree_coordinates()
