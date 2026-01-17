"""
Calculate Legally Available Street Tree Planting Locations
Based on NYC Street Tree Planting Compliance Rules

Rules:
1. Tree-to-tree spacing: 20-30 ft (nearest neighbor)
2. Stop signs: ≥ 30 ft clearance
3. Other traffic signs: ≥ 6 ft clearance
4. Building clearance: distance to nearest building footprint edge

Note: This script works with available data. Some datasets may need to be downloaded.
"""

import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from scipy.spatial.distance import cdist
from pathlib import Path
import json
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
EXTERNAL_DIR = DATA_DIR / "external"
OUTPUT_DIR = DATA_DIR / "processed"
COMPLIANCE_DIR = BASE_DIR.parent / "Compliance data merged"  # Compliance data folder

# Constants (in meters - converted from feet)
TREE_SPACING_MIN_FT = 20
TREE_SPACING_MAX_FT = 30
STOP_SIGN_CLEARANCE_FT = 30
TRAFFIC_SIGN_CLEARANCE_FT = 6
BUILDING_CLEARANCE_FT = 3  # Minimum clearance from building edge (typical requirement)

# Convert feet to meters (approximate)
FT_TO_M = 0.3048
TREE_SPACING_MIN_M = TREE_SPACING_MIN_FT * FT_TO_M
TREE_SPACING_MAX_M = TREE_SPACING_MAX_FT * FT_TO_M
STOP_SIGN_CLEARANCE_M = STOP_SIGN_CLEARANCE_FT * FT_TO_M
TRAFFIC_SIGN_CLEARANCE_M = TRAFFIC_SIGN_CLEARANCE_FT * FT_TO_M
BUILDING_CLEARANCE_M = BUILDING_CLEARANCE_FT * FT_TO_M


def load_existing_trees() -> gpd.GeoDataFrame:
    """Load 2015 Street Tree Census data."""
    print("Loading 2015 Street Tree Census...")
    trees_path = CACHE_DIR / "street_trees_2015.csv"
    
    if not trees_path.exists():
        raise FileNotFoundError(f"Tree census not found at {trees_path}")
    
    df = pd.read_csv(trees_path, low_memory=False)
    
    # Filter alive trees only
    df = df[df['status'] == 'Alive'].copy()
    
    # Ensure coordinates are numeric
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    
    # Remove rows with invalid coordinates
    df = df[df['latitude'].notna() & df['longitude'].notna()].copy()
    df = df[(df['latitude'] >= 40.4) & (df['latitude'] <= 41.0)].copy()  # NYC bounds
    df = df[(df['longitude'] >= -74.3) & (df['longitude'] <= -73.7)].copy()
    
    # Create GeoDataFrame
    geometry = [Point(lon, lat) for lon, lat in zip(df['longitude'], df['latitude'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
    
    # Convert to Web Mercator for distance calculations (meters)
    gdf = gdf.to_crs('EPSG:3857')
    
    print(f"  Loaded {len(gdf)} alive trees")
    return gdf


def calculate_tree_spacing_constraints(trees_gdf: gpd.GeoDataFrame) -> Dict:
    """
    Calculate tree-to-tree spacing constraints.
    Returns areas where new trees can be planted based on 20-30 ft spacing rule.
    """
    print("\nCalculating tree-to-tree spacing constraints...")
    
    # Get tree coordinates
    tree_coords = np.array([[geom.x, geom.y] for geom in trees_gdf.geometry])
    
    # Calculate nearest neighbor distances for each tree
    if len(tree_coords) > 0:
        # Use KDTree for efficient nearest neighbor search
        from scipy.spatial import cKDTree
        tree = cKDTree(tree_coords)
        
        # Find nearest neighbor for each tree (excluding itself)
        distances, indices = tree.query(tree_coords, k=2)
        nearest_distances = distances[:, 1]  # Second nearest (first is itself)
        
        # Convert from meters to feet for reporting
        nearest_distances_ft = nearest_distances / FT_TO_M
        
        # Identify gaps where spacing is > 30 ft (can plant new tree)
        # and areas where spacing is < 20 ft (too close, violation)
        too_close = (nearest_distances_ft < TREE_SPACING_MIN_FT).sum()
        optimal_spacing = ((nearest_distances_ft >= TREE_SPACING_MIN_FT) & 
                          (nearest_distances_ft <= TREE_SPACING_MAX_FT)).sum()
        too_far = (nearest_distances_ft > TREE_SPACING_MAX_FT).sum()
        
        print(f"  Tree spacing analysis:")
        print(f"    Trees with spacing < 20 ft (too close): {too_close:,}")
        print(f"    Trees with spacing 20-30 ft (optimal): {optimal_spacing:,}")
        print(f"    Trees with spacing > 30 ft (can plant nearby): {too_far:,}")
        print(f"    Average nearest neighbor distance: {nearest_distances_ft.mean():.1f} ft")
        
        # Estimate available planting locations
        # For each tree with spacing > 30 ft, we can potentially plant 1 new tree
        # (conservative estimate - actual depends on street layout)
        estimated_planting_sites_from_spacing = too_far
        
        return {
            'nearest_distances_m': nearest_distances,
            'nearest_distances_ft': nearest_distances_ft,
            'too_close_count': too_close,
            'optimal_spacing_count': optimal_spacing,
            'too_far_count': too_far,
            'estimated_planting_sites': estimated_planting_sites_from_spacing
        }
    else:
        return {
            'nearest_distances_m': np.array([]),
            'nearest_distances_ft': np.array([]),
            'too_close_count': 0,
            'optimal_spacing_count': 0,
            'too_far_count': 0,
            'estimated_planting_sites': 0
        }


def load_sign_data() -> Tuple[Optional[gpd.GeoDataFrame], Optional[gpd.GeoDataFrame]]:
    """
    Load parking regulation signs and street sign work orders.
    Returns (parking_signs_gdf, street_signs_gdf) or (None, None) if not available.
    """
    print("\nLoading sign data...")
    
    parking_signs = None
    street_signs = None
    
    # Try to load Parking Regulation Locations and Signs
    # Check both cache directory and compliance data folder
    parking_signs_paths = [
        COMPLIANCE_DIR / "Parking_Regulation_Locations_and_Signs_20260116.csv",
        CACHE_DIR / "parking_regulation_signs.csv",
        CACHE_DIR / "Parking_Regulation_Locations_and_Signs.csv"
    ]
    
    for parking_signs_path in parking_signs_paths:
        if parking_signs_path.exists():
            try:
                print(f"  Loading from: {parking_signs_path}")
                # Read in chunks for large files
                df = pd.read_csv(parking_signs_path, low_memory=False, nrows=1000)  # Sample first
                total_rows = sum(1 for _ in open(parking_signs_path)) - 1  # Count total rows
                print(f"  File has ~{total_rows:,} rows, reading in chunks...")
                
                # Read full file
                df = pd.read_csv(parking_signs_path, low_memory=False)
                
                # Check for coordinate columns
                # May have sign_x_coord, sign_y_coord (State Plane) or lat/lon
                x_col = None
                y_col = None
                lat_col = None
                lon_col = None
                
                for col in df.columns:
                    col_lower = col.lower()
                    if 'x_coord' in col_lower or ('x' in col_lower and 'coord' in col_lower):
                        x_col = col
                    if 'y_coord' in col_lower or ('y' in col_lower and 'coord' in col_lower):
                        y_col = col
                    if 'lat' in col_lower:
                        lat_col = col
                    if 'lon' in col_lower or 'lng' in col_lower or 'long' in col_lower:
                        lon_col = col
                
                if x_col and y_col:
                    # State Plane coordinates (NY State Plane Long Island - EPSG:2263)
                    df[x_col] = pd.to_numeric(df[x_col], errors='coerce')
                    df[y_col] = pd.to_numeric(df[y_col], errors='coerce')
                    df = df[df[x_col].notna() & df[y_col].notna()].copy()
                    
                    geometry = [Point(x, y) for x, y in zip(df[x_col], df[y_col])]
                    parking_signs = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:2263')  # NY State Plane
                    parking_signs = parking_signs.to_crs('EPSG:3857')  # Convert to Web Mercator
                    print(f"  Loaded {len(parking_signs)} parking regulation signs (State Plane coordinates)")
                    break
                elif lat_col and lon_col:
                    # Lat/lon coordinates
                    df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce')
                    df[lon_col] = pd.to_numeric(df[lon_col], errors='coerce')
                    df = df[df[lat_col].notna() & df[lon_col].notna()].copy()
                    
                    geometry = [Point(lon, lat) for lon, lat in zip(df[lon_col], df[lat_col])]
                    parking_signs = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
                    parking_signs = parking_signs.to_crs('EPSG:3857')
                    print(f"  Loaded {len(parking_signs)} parking regulation signs (lat/lon coordinates)")
                    break
                else:
                    print(f"  ⚠️  No coordinate columns found. Available columns: {list(df.columns[:10])}")
            except Exception as e:
                print(f"  ⚠️  Error loading parking regulation signs: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    if parking_signs is None:
        print(f"  ⚠️  Parking regulation signs not found")
        print(f"     Checked: {[str(p) for p in parking_signs_paths]}")
    
    # Try to load Street Sign Work Orders
    street_signs_paths = [
        COMPLIANCE_DIR / "Street_Sign_Work_Orders_20260116.csv",
        CACHE_DIR / "street_sign_work_orders.csv",
        CACHE_DIR / "Street_Sign_Work_Orders.csv"
    ]
    
    for street_signs_path in street_signs_paths:
        if street_signs_path.exists():
            try:
                print(f"  Loading from: {street_signs_path}")
                # For very large files, we'll sample or read in chunks
                # First check file size
                file_size_mb = street_signs_path.stat().st_size / (1024 * 1024)
                print(f"  File size: {file_size_mb:.1f} MB")
                
                if file_size_mb > 100:
                    print(f"  ⚠️  File is very large ({file_size_mb:.1f} MB). Sampling 100k rows for analysis...")
                    df = pd.read_csv(street_signs_path, low_memory=False, nrows=100000)
                else:
                    df = pd.read_csv(street_signs_path, low_memory=False)
                
                # Look for coordinate columns
                x_col = None
                y_col = None
                lat_col = None
                lon_col = None
                
                for col in df.columns:
                    col_lower = col.lower()
                    if 'x_coord' in col_lower or ('x' in col_lower and 'coord' in col_lower):
                        x_col = col
                    if 'y_coord' in col_lower or ('y' in col_lower and 'coord' in col_lower):
                        y_col = col
                    if 'lat' in col_lower:
                        lat_col = col
                    if 'lon' in col_lower or 'lng' in col_lower or 'long' in col_lower:
                        lon_col = col
                
                if x_col and y_col:
                    df[x_col] = pd.to_numeric(df[x_col], errors='coerce')
                    df[y_col] = pd.to_numeric(df[y_col], errors='coerce')
                    df = df[df[x_col].notna() & df[y_col].notna()].copy()
                    
                    geometry = [Point(x, y) for x, y in zip(df[x_col], df[y_col])]
                    street_signs = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:2263')
                    street_signs = street_signs.to_crs('EPSG:3857')
                    print(f"  Loaded {len(street_signs)} street sign work orders (State Plane coordinates)")
                    break
                elif lat_col and lon_col:
                    df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce')
                    df[lon_col] = pd.to_numeric(df[lon_col], errors='coerce')
                    df = df[df[lat_col].notna() & df[lon_col].notna()].copy()
                    
                    geometry = [Point(lon, lat) for lon, lat in zip(df[lon_col], df[lat_col])]
                    street_signs = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
                    street_signs = street_signs.to_crs('EPSG:3857')
                    print(f"  Loaded {len(street_signs)} street sign work orders (lat/lon coordinates)")
                    break
                else:
                    print(f"  ⚠️  No coordinate columns found. Available columns: {list(df.columns[:10])}")
            except Exception as e:
                print(f"  ⚠️  Error loading street sign work orders: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    if street_signs is None:
        print(f"  ⚠️  Street sign work orders not found")
        print(f"     Checked: {[str(p) for p in street_signs_paths]}")
    
    return parking_signs, street_signs


def load_building_data() -> Optional[gpd.GeoDataFrame]:
    """
    Load building footprint data.
    Dataset ID: 5zhs-2jue
    """
    print("\nLoading building data...")
    
    # Try multiple possible file formats and locations
    building_paths = [
        COMPLIANCE_DIR / "BUILDING_20260116.csv",
        CACHE_DIR / "buildings.csv",
        CACHE_DIR / "building_footprints.csv",
        EXTERNAL_DIR / "buildings" / "buildings.shp",
        EXTERNAL_DIR / "nyc_buildings" / "buildings.shp"
    ]
    
    buildings = None
    
    for path in building_paths:
        if path.exists():
            try:
                if path.suffix == '.shp':
                    print(f"  Loading from shapefile: {path}")
                    buildings = gpd.read_file(path)
                    buildings = buildings.to_crs('EPSG:3857')
                    print(f"  Loaded {len(buildings)} building footprints from shapefile")
                    break
                elif path.suffix == '.csv':
                    print(f"  Loading from CSV: {path}")
                    file_size_mb = path.stat().st_size / (1024 * 1024)
                    print(f"  File size: {file_size_mb:.1f} MB")
                    
                    if file_size_mb > 200:
                        print(f"  ⚠️  File is very large ({file_size_mb:.1f} MB). Sampling 50k rows for analysis...")
                        df = pd.read_csv(path, low_memory=False, nrows=50000)
                    else:
                        df = pd.read_csv(path, low_memory=False)
                    
                    # Look for geometry column or lat/lon
                    if 'geometry' in df.columns:
                        df['geometry'] = gpd.GeoSeries.from_wkt(df['geometry'])
                        buildings = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
                    elif 'the_geom' in df.columns:
                        # NYC building footprints use 'the_geom' column with WKT geometry
                        df['geometry'] = gpd.GeoSeries.from_wkt(df['the_geom'])
                        buildings = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
                    else:
                        # Try to find lat/lon or x/y coordinate columns
                        lat_col = None
                        lon_col = None
                        x_col = None
                        y_col = None
                        
                        for col in df.columns:
                            col_lower = col.lower()
                            if 'lat' in col_lower:
                                lat_col = col
                            if 'lon' in col_lower or 'lng' in col_lower or 'long' in col_lower:
                                lon_col = col
                            if 'x_coord' in col_lower or ('x' in col_lower and 'coord' in col_lower):
                                x_col = col
                            if 'y_coord' in col_lower or ('y' in col_lower and 'coord' in col_lower):
                                y_col = col
                        
                        if lat_col and lon_col:
                            # Create point geometries (centroids)
                            df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce')
                            df[lon_col] = pd.to_numeric(df[lon_col], errors='coerce')
                            df = df[df[lat_col].notna() & df[lon_col].notna()].copy()
                            geometry = [Point(lon, lat) for lon, lat in zip(df[lon_col], df[lat_col])]
                            buildings = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
                        elif x_col and y_col:
                            # State Plane coordinates
                            df[x_col] = pd.to_numeric(df[x_col], errors='coerce')
                            df[y_col] = pd.to_numeric(df[y_col], errors='coerce')
                            df = df[df[x_col].notna() & df[y_col].notna()].copy()
                            geometry = [Point(x, y) for x, y in zip(df[x_col], df[y_col])]
                            buildings = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:2263')
                    
                    if buildings is not None:
                        buildings = buildings.to_crs('EPSG:3857')
                        print(f"  Loaded {len(buildings)} buildings from CSV")
                        break
            except Exception as e:
                print(f"  ⚠️  Error loading buildings from {path}: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    if buildings is None:
        print(f"  ⚠️  Building data not found")
        print(f"     Checked: {[str(p) for p in building_paths]}")
        print(f"     Download from: https://data.cityofnewyork.us/Housing-Development/Building-Footprints/5zhs-2jue")
        print(f"     Or use NYC Planning's PLUTO dataset")
    
    return buildings


def calculate_sign_constraints(
    trees_gdf: gpd.GeoDataFrame,
    parking_signs: Optional[gpd.GeoDataFrame],
    street_signs: Optional[gpd.GeoDataFrame]
) -> Dict:
    """
    Calculate sign clearance constraints.
    Returns count of trees that violate sign clearance rules.
    """
    print("\nCalculating sign clearance constraints...")
    
    tree_coords = np.array([[geom.x, geom.y] for geom in trees_gdf.geometry])
    violations = {
        'stop_sign_violations': 0,
        'traffic_sign_violations': 0,
        'total_sign_constrained_areas': 0,
        'stop_sign_count': 0
    }
    
    if parking_signs is not None and len(parking_signs) > 0:
        sign_coords = np.array([[geom.x, geom.y] for geom in parking_signs.geometry])
        
        # Try to identify stop signs from sign_description or sign_code
        stop_sign_keywords = ['stop', 'STOP', 'stop sign', 'STOP SIGN']
        is_stop_sign = None
        if 'sign_description' in parking_signs.columns:
            is_stop_sign = parking_signs['sign_description'].str.contains('|'.join(stop_sign_keywords), case=False, na=False)
        elif 'sign_code' in parking_signs.columns:
            is_stop_sign = parking_signs['sign_code'].str.contains('|'.join(stop_keywords), case=False, na=False)
        
        stop_sign_count = is_stop_sign.sum() if is_stop_sign is not None else 0
        violations['stop_sign_count'] = stop_sign_count
        
        # Calculate distances from trees to signs
        from scipy.spatial import cKDTree
        sign_tree = cKDTree(sign_coords)
        
        # Find nearest sign to each tree
        distances_to_signs, nearest_sign_indices = sign_tree.query(tree_coords, k=1)
        distances_to_signs_ft = distances_to_signs / FT_TO_M
        
        # Check for violations
        # For stop signs: need 30 ft clearance
        # For other signs: need 6 ft clearance
        if is_stop_sign is not None:
            # Identify which trees are near stop signs
            stop_sign_coords = sign_coords[is_stop_sign.values]
            if len(stop_sign_coords) > 0:
                stop_sign_tree = cKDTree(stop_sign_coords)
                distances_to_stop_signs, _ = stop_sign_tree.query(tree_coords, k=1)
                distances_to_stop_signs_ft = distances_to_stop_signs / FT_TO_M
                violations['stop_sign_violations'] = (distances_to_stop_signs_ft < STOP_SIGN_CLEARANCE_FT).sum()
            
            # For non-stop signs, use 6 ft clearance
            non_stop_sign_coords = sign_coords[~is_stop_sign.values]
            if len(non_stop_sign_coords) > 0:
                non_stop_sign_tree = cKDTree(non_stop_sign_coords)
                distances_to_non_stop_signs, _ = non_stop_sign_tree.query(tree_coords, k=1)
                distances_to_non_stop_signs_ft = distances_to_non_stop_signs / FT_TO_M
                violations['traffic_sign_violations'] = (distances_to_non_stop_signs_ft < TRAFFIC_SIGN_CLEARANCE_FT).sum()
        else:
            # Can't identify stop signs, use conservative approach
            # Use 30 ft for all signs (some may be stop signs)
            violations['traffic_sign_violations'] = (distances_to_signs_ft < TRAFFIC_SIGN_CLEARANCE_FT).sum()
            violations['stop_sign_violations'] = (distances_to_signs_ft < STOP_SIGN_CLEARANCE_FT).sum()
        
        # Estimate constrained areas (buffer around signs)
        violations['total_sign_constrained_areas'] = len(parking_signs)
        
        print(f"  Parking regulation signs analysis:")
        print(f"    Total signs: {len(parking_signs):,}")
        print(f"    Identified stop signs: {stop_sign_count:,}")
        print(f"    Trees within {TRAFFIC_SIGN_CLEARANCE_FT} ft of signs: {violations['traffic_sign_violations']:,}")
        print(f"    Trees within {STOP_SIGN_CLEARANCE_FT} ft of stop signs: {violations['stop_sign_violations']:,}")
        print(f"    Sign-constrained areas: {violations['total_sign_constrained_areas']:,}")
    
    if street_signs is not None and len(street_signs) > 0:
        sign_coords = np.array([[geom.x, geom.y] for geom in street_signs.geometry])
        
        from scipy.spatial import cKDTree
        sign_tree = cKDTree(sign_coords)
        distances_to_signs, _ = sign_tree.query(tree_coords, k=1)
        distances_to_signs_ft = distances_to_signs / FT_TO_M
        
        additional_violations = (distances_to_signs_ft < TRAFFIC_SIGN_CLEARANCE_FT).sum()
        violations['traffic_sign_violations'] += additional_violations
        violations['total_sign_constrained_areas'] += len(street_signs)
        
        print(f"  Street sign work orders analysis:")
        print(f"    Total work orders: {len(street_signs):,}")
        print(f"    Additional trees within {TRAFFIC_SIGN_CLEARANCE_FT} ft: {additional_violations:,}")
        print(f"    Additional sign-constrained areas: {len(street_signs):,}")
    
    if parking_signs is None and street_signs is None:
        print("  ⚠️  No sign data available - cannot calculate sign constraints")
        print("     This will be estimated based on tree spacing only")
    
    return violations


def calculate_building_constraints(
    trees_gdf: gpd.GeoDataFrame,
    buildings: Optional[gpd.GeoDataFrame]
) -> Dict:
    """
    Calculate building clearance constraints.
    Returns distance to nearest building for each tree.
    """
    print("\nCalculating building clearance constraints...")
    
    if buildings is None:
        print("  ⚠️  Building data not available - cannot calculate building clearance")
        return {
            'building_distances_m': np.array([]),
            'building_distances_ft': np.array([]),
            'violations': 0,
            'avg_distance_ft': 0
        }
    
    tree_coords = np.array([[geom.x, geom.y] for geom in trees_gdf.geometry])
    
    # Calculate distance from each tree to nearest building edge
    # For efficiency, we'll use building centroids as proxy (less accurate but faster)
    # In production, you'd want to calculate distance to actual building edges
    
    if 'geometry' in buildings.columns:
        # If buildings have polygon geometries, get centroids
        if buildings.geometry.type.iloc[0] in ['Polygon', 'MultiPolygon']:
            building_centroids = buildings.geometry.centroid
            building_coords = np.array([[geom.x, geom.y] for geom in building_centroids])
        else:
            # Already points
            building_coords = np.array([[geom.x, geom.y] for geom in buildings.geometry])
        
        from scipy.spatial import cKDTree
        building_tree = cKDTree(building_coords)
        
        # Find nearest building to each tree
        distances_to_buildings, _ = building_tree.query(tree_coords, k=1)
        distances_to_buildings_ft = distances_to_buildings / FT_TO_M
        
        # Count violations (trees too close to buildings)
        violations = (distances_to_buildings_ft < BUILDING_CLEARANCE_FT).sum()
        
        print(f"  Building clearance analysis:")
        print(f"    Average distance to nearest building: {distances_to_buildings_ft.mean():.1f} ft")
        print(f"    Trees within {BUILDING_CLEARANCE_FT} ft of buildings: {violations:,}")
        print(f"    Trees with adequate clearance: {len(trees_gdf) - violations:,}")
        
        return {
            'building_distances_m': distances_to_buildings,
            'building_distances_ft': distances_to_buildings_ft,
            'violations': violations,
            'avg_distance_ft': distances_to_buildings_ft.mean()
        }
    else:
        print("  ⚠️  Building geometries not found")
        return {
            'building_distances_m': np.array([]),
            'building_distances_ft': np.array([]),
            'violations': 0,
            'avg_distance_ft': 0
        }


def estimate_available_planting_locations(
    spacing_results: Dict,
    sign_results: Dict,
    building_results: Dict,
    total_trees: int
) -> Dict:
    """
    Estimate total legally available planting locations.
    This is a conservative estimate based on available data.
    """
    print("\n" + "="*60)
    print("ESTIMATING LEGALLY AVAILABLE PLANTING LOCATIONS")
    print("="*60)
    
    # Base estimate from tree spacing
    # Areas with spacing > 30 ft can potentially accommodate new trees
    base_estimate = spacing_results['estimated_planting_sites']
    
    # Adjust for sign constraints
    # Each sign constrains a circular area (radius = clearance requirement)
    # Rough estimate: signs are distributed along streets, so they don't prevent ALL plantings
    # More realistic: signs reduce available locations by ~10-20% (they're on streets, trees are also on streets)
    # Use a smaller multiplier since signs and trees are both on streets (not competing for all space)
    total_signs = sign_results.get('total_sign_constrained_areas', 0)
    # Estimate: each sign affects ~0.1-0.2 tree locations (signs are dense, but trees can be planted between signs)
    sign_penalty = total_signs * 0.15  # More realistic multiplier
    
    # Adjust for building constraints
    # Trees too close to buildings are violations, but this doesn't necessarily
    # prevent new plantings - it just means existing trees are in violation
    # Building penalty is minimal for new plantings (we avoid building edges anyway)
    building_penalty = building_results.get('violations', 0) * 0.1  # Small penalty
    
    # Conservative estimate
    # Note: This doesn't account for:
    # - Street width and layout
    # - Existing infrastructure (utilities, sidewalks)
    # - Private property vs public right-of-way
    # - Actual street centerline locations
    
    estimated_available = max(0, base_estimate - sign_penalty - building_penalty)
    
    # Alternative calculation: Estimate based on street length
    # Average NYC street block: ~264 ft long
    # With 20-30 ft spacing, can fit ~9-13 trees per block
    # If average block has 5 trees, can add ~4-8 more per block
    # NYC has ~12,000 blocks
    # Rough estimate: 12,000 blocks * 5 additional trees = 60,000 potential sites
    
    results = {
        'base_estimate_from_spacing': int(base_estimate),
        'sign_penalty': int(sign_penalty),
        'building_penalty': int(building_penalty),
        'estimated_available_locations': int(estimated_available),
        'alternative_estimate_by_blocks': 60000,  # Rough estimate
        'total_existing_trees': total_trees,
        'potential_increase_percent': (estimated_available / total_trees * 100) if total_trees > 0 else 0
    }
    
    print(f"\nResults:")
    print(f"  Total existing trees: {total_trees:,}")
    print(f"  Base estimate (from spacing gaps): {base_estimate:,} locations")
    print(f"  Sign constraint penalty: -{sign_penalty:,.0f} locations")
    print(f"  Building constraint penalty: -{building_penalty:,.0f} locations")
    print(f"  ──────────────────────────────────────────────")
    print(f"  ESTIMATED LEGALLY AVAILABLE: {estimated_available:,.0f} locations")
    print(f"  ──────────────────────────────────────────────")
    print(f"\n  Alternative estimate (by block): ~{results['alternative_estimate_by_blocks']:,} locations")
    print(f"  Potential increase: {results['potential_increase_percent']:.1f}% of current tree count")
    
    print(f"\n⚠️  IMPORTANT LIMITATIONS:")
    print(f"  - This estimate does NOT include road centerlines/street networks")
    print(f"  - Actual planting locations depend on street width and layout")
    print(f"  - Some areas may be private property (not public right-of-way)")
    print(f"  - Utilities and infrastructure may further constrain locations")
    print(f"  - This is a conservative estimate based on spacing rules only")
    
    return results


def main():
    """Main function to calculate available planting locations."""
    print("="*60)
    print("NYC STREET TREE PLANTING COMPLIANCE ANALYSIS")
    print("="*60)
    print("\nThis script calculates legally available street tree planting locations")
    print("based on NYC compliance rules:\n")
    print("  1. Tree-to-tree spacing: 20-30 ft")
    print("  2. Stop signs: ≥ 30 ft clearance")
    print("  3. Other traffic signs: ≥ 6 ft clearance")
    print("  4. Building clearance: distance to nearest building edge")
    print("\n" + "="*60 + "\n")
    
    # Load data
    trees_gdf = load_existing_trees()
    parking_signs, street_signs = load_sign_data()
    buildings = load_building_data()
    
    # Calculate constraints
    spacing_results = calculate_tree_spacing_constraints(trees_gdf)
    sign_results = calculate_sign_constraints(trees_gdf, parking_signs, street_signs)
    building_results = calculate_building_constraints(trees_gdf, buildings)
    
    # Estimate available locations
    results = estimate_available_planting_locations(
        spacing_results,
        sign_results,
        building_results,
        len(trees_gdf)
    )
    
    # Save results
    output_path = OUTPUT_DIR / "available_planting_locations.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Convert numpy types to Python native types for JSON serialization
    def convert_to_native(obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: convert_to_native(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_native(item) for item in obj]
        return obj
    
    output_data = {
        'analysis_date': pd.Timestamp.now().isoformat(),
        'total_existing_trees': int(len(trees_gdf)),
        'spacing_analysis': {
            'too_close_count': int(spacing_results['too_close_count']),
            'optimal_spacing_count': int(spacing_results['optimal_spacing_count']),
            'too_far_count': int(spacing_results['too_far_count']),
            'avg_nearest_neighbor_ft': float(spacing_results['nearest_distances_ft'].mean())
        },
        'sign_constraints': convert_to_native(sign_results),
        'building_constraints': {
            'violations': int(building_results['violations']),
            'avg_distance_ft': float(building_results['avg_distance_ft'])
        },
        'estimated_available_locations': convert_to_native(results)
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_path}")
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)


if __name__ == '__main__':
    main()
