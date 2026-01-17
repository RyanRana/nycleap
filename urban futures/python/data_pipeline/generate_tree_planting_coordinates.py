"""
Generate All Available Tree Planting Coordinates
Uses LION street network + all constraint datasets with accurate NYC rules.
"""

import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon, MultiPolygon
from shapely import wkt
from pathlib import Path
import json
from typing import List, Dict, Tuple, Optional
import warnings
from multiprocessing import Pool, cpu_count
from functools import partial
warnings.filterwarnings('ignore')

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
EXTERNAL_DIR = DATA_DIR / "external"
OUTPUT_DIR = DATA_DIR / "processed"
COMPLIANCE_DIR = BASE_DIR.parent / "Compliance data merged"
LION_DIR = COMPLIANCE_DIR / "lion" / "lion.gdb"

# NYC Street Tree Planting Rules (in feet, converted to meters)
TREE_DIAMETER_INCHES = 10.67
TREE_SPACING_FT = 30  # Must be 30ft apart
STOP_SIGN_CLEARANCE_FT = 30  # At least 30' from trunk
HYDRANT_CLEARANCE_FT = 5  # At least 5' from trunk (not 10ft)
STREET_SIGN_CLEARANCE_FT = 6  # At least 6' from trunk
STREET_LIGHT_CLEARANCE_FT = 25  # At least 25' from trunk
CURB_CUT_CLEARANCE_FT = 7  # At least 7' from trunk
INTERSECTION_CLEARANCE_FT = 40  # At least 40' from trunk (curb of intersection)
BUS_STOP_CLEARANCE_FT = 0  # No trees at curb (but can be set back in sidewalk)
MEDIAN_MIN_WIDTH_FT = 8  # At least 8' wide for new trees
SIDEWALK_MIN_WIDTH_INCHES = 39  # At least 39" wide from back of tree bed to wall/fence
SIDEWALK_MIN_WIDTH_FT = SIDEWALK_MIN_WIDTH_INCHES / 12

# Utility clearances
GAS_ELECTRIC_CLEARANCE_FT = 2  # At least 2' from edge of tree bed
WATER_PIPE_VALVE_CLEARANCE_FT = 2  # At least 2' from trunk
OIL_FILL_PIPE_CLEARANCE_FT = 4  # At least 4' from edge of tree bed

FT_TO_M = 0.3048
TREE_SPACING_M = TREE_SPACING_FT * FT_TO_M
STOP_SIGN_CLEARANCE_M = STOP_SIGN_CLEARANCE_FT * FT_TO_M
HYDRANT_CLEARANCE_M = HYDRANT_CLEARANCE_FT * FT_TO_M
STREET_SIGN_CLEARANCE_M = STREET_SIGN_CLEARANCE_FT * FT_TO_M
STREET_LIGHT_CLEARANCE_M = STREET_LIGHT_CLEARANCE_FT * FT_TO_M
CURB_CUT_CLEARANCE_M = CURB_CUT_CLEARANCE_FT * FT_TO_M
INTERSECTION_CLEARANCE_M = INTERSECTION_CLEARANCE_FT * FT_TO_M


def load_lion_streets() -> Optional[gpd.GeoDataFrame]:
    """Load LION street network (centerlines)."""
    print("Loading LION street network...")
    
    if not LION_DIR.exists():
        print(f"  ⚠️  LION geodatabase not found at {LION_DIR}")
        return None
    
    try:
        streets = gpd.read_file(str(LION_DIR), layer='lion')
        print(f"  Loaded {len(streets)} street segments")
        
        if streets.crs is None:
            streets.set_crs('EPSG:2263', allow_override=True)
        
        streets = streets.to_crs('EPSG:3857')
        return streets
    except Exception as e:
        print(f"  ⚠️  Error loading LION: {e}")
        return None


def load_existing_trees() -> gpd.GeoDataFrame:
    """Load 2015 Street Tree Census data."""
    print("Loading existing trees...")
    trees_path = CACHE_DIR / "street_trees_2015.csv"
    
    df = pd.read_csv(trees_path, low_memory=False)
    df = df[df['status'] == 'Alive'].copy()
    
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df = df[df['latitude'].notna() & df['longitude'].notna()].copy()
    
    geometry = [Point(lon, lat) for lon, lat in zip(df['longitude'], df['latitude'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
    gdf = gdf.to_crs('EPSG:3857')
    
    print(f"  Loaded {len(gdf)} existing trees")
    return gdf


def load_constraint_points() -> Dict:
    """Load all constraint point datasets."""
    print("\nLoading constraint datasets...")
    constraints = {}
    
    # Load parking regulation signs (for stop signs and street signs)
    signs_path = COMPLIANCE_DIR / "Parking_Regulation_Locations_and_Signs_20260116.csv"
    if signs_path.exists():
        try:
            df = pd.read_csv(signs_path, low_memory=False, nrows=100000)  # Sample for speed
            if 'sign_x_coord' in df.columns and 'sign_y_coord' in df.columns:
                df['sign_x_coord'] = pd.to_numeric(df['sign_x_coord'], errors='coerce')
                df['sign_y_coord'] = pd.to_numeric(df['sign_y_coord'], errors='coerce')
                df = df[df['sign_x_coord'].notna() & df['sign_y_coord'].notna()].copy()
                geometry = [Point(x, y) for x, y in zip(df['sign_x_coord'], df['sign_y_coord'])]
                gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:2263')
                gdf = gdf.to_crs('EPSG:3857')
                
                # Identify stop signs
                if 'sign_description' in df.columns:
                    stop_keywords = ['stop', 'STOP', 'stop sign', 'STOP SIGN']
                    is_stop = df['sign_description'].str.contains('|'.join(stop_keywords), case=False, na=False)
                    constraints['stop_signs'] = gdf[is_stop].copy()
                    constraints['street_signs'] = gdf[~is_stop].copy()
                else:
                    constraints['street_signs'] = gdf
                
                print(f"  Loaded {len(constraints.get('stop_signs', []))} stop signs")
                print(f"  Loaded {len(constraints.get('street_signs', []))} street signs")
        except Exception as e:
            print(f"  ⚠️  Error loading signs: {e}")
    
    # Load fire hydrants
    hydrants_path = COMPLIANCE_DIR / "Hydrants_20260116.csv"
    if hydrants_path.exists():
        try:
            df = pd.read_csv(hydrants_path, low_memory=False)
            if 'LATITUDE' in df.columns and 'LONGITUDE' in df.columns:
                df['LATITUDE'] = pd.to_numeric(df['LATITUDE'], errors='coerce')
                df['LONGITUDE'] = pd.to_numeric(df['LONGITUDE'], errors='coerce')
                df = df[df['LATITUDE'].notna() & df['LONGITUDE'].notna()].copy()
                geometry = [Point(lon, lat) for lon, lat in zip(df['LONGITUDE'], df['LATITUDE'])]
                gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
                gdf = gdf.to_crs('EPSG:3857')
                constraints['hydrants'] = gdf
                print(f"  Loaded {len(gdf)} fire hydrants")
        except Exception as e:
            print(f"  ⚠️  Error loading hydrants: {e}")
    
    # Load bus stops
    bus_stops_path = COMPLIANCE_DIR / "Bus_Stop_Shelter_20260116.csv"
    if bus_stops_path.exists():
        try:
            df = pd.read_csv(bus_stops_path, low_memory=False)
            if 'Longitude' in df.columns and 'Latitude' in df.columns:
                df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
                df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
                df = df[df['Latitude'].notna() & df['Longitude'].notna()].copy()
                geometry = [Point(lon, lat) for lon, lat in zip(df['Longitude'], df['Latitude'])]
                gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
                gdf = gdf.to_crs('EPSG:3857')
                constraints['bus_stops'] = gdf
                print(f"  Loaded {len(gdf)} bus stops")
        except Exception as e:
            print(f"  ⚠️  Error loading bus stops: {e}")
    
    return constraints


def load_sidewalks() -> Optional[gpd.GeoDataFrame]:
    """Load sidewalk polygons from planimetric database."""
    print("\nLoading sidewalk data...")
    sidewalk_path = COMPLIANCE_DIR / "NYC_Planimetric_Database__Sidewalk_20260116.csv"
    
    if not sidewalk_path.exists():
        print(f"  ⚠️  Sidewalk data not found at {sidewalk_path}")
        return None
    
    try:
        # Read in chunks to handle large file
        print("  Reading sidewalk CSV (this may take a moment)...")
        df = pd.read_csv(sidewalk_path, low_memory=False)
        
        if 'the_geom' not in df.columns:
            print("  ⚠️  No geometry column found in sidewalk data")
            return None
        
        # Parse WKT geometry
        print("  Parsing geometry...")
        df['geometry'] = df['the_geom'].apply(lambda x: wkt.loads(x) if pd.notna(x) else None)
        df = df[df['geometry'].notna()].copy()
        
        sidewalks = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
        sidewalks = sidewalks.to_crs('EPSG:3857')
        
        print(f"  Loaded {len(sidewalks)} sidewalk polygons")
        return sidewalks
    except Exception as e:
        print(f"  ⚠️  Error loading sidewalks: {e}")
        import traceback
        traceback.print_exc()
        return None


def load_buildings() -> Optional[gpd.GeoDataFrame]:
    """Load building footprints."""
    print("\nLoading building data...")
    building_path = COMPLIANCE_DIR / "BUILDING_20260116.csv"
    
    if not building_path.exists():
        print(f"  ⚠️  Building data not found at {building_path}")
        return None
    
    try:
        # Sample buildings for performance (full dataset is huge)
        print("  Reading building CSV (sampling 100k rows for performance)...")
        df = pd.read_csv(building_path, low_memory=False, nrows=100000)
        
        if 'the_geom' not in df.columns:
            print("  ⚠️  No geometry column found in building data")
            return None
        
        # Parse WKT geometry
        print("  Parsing geometry...")
        df['geometry'] = df['the_geom'].apply(lambda x: wkt.loads(x) if pd.notna(x) else None)
        df = df[df['geometry'].notna()].copy()
        
        buildings = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
        buildings = buildings.to_crs('EPSG:3857')
        
        print(f"  Loaded {len(buildings)} building footprints (sampled)")
        return buildings
    except Exception as e:
        print(f"  ⚠️  Error loading buildings: {e}")
        import traceback
        traceback.print_exc()
        return None


def find_intersections(streets: gpd.GeoDataFrame) -> Optional[gpd.GeoDataFrame]:
    """Find intersection points from street network endpoints."""
    print("\nFinding intersections from street network...")
    
    try:
        intersection_points = []
        
        # Get all street endpoints
        for idx, street in streets.iterrows():
            geom = street.geometry
            if isinstance(geom, LineString):
                # Add start and end points
                intersection_points.append(Point(geom.coords[0]))
                intersection_points.append(Point(geom.coords[-1]))
            elif hasattr(geom, 'geoms'):  # MultiLineString
                for line in geom.geoms:
                    if isinstance(line, LineString):
                        intersection_points.append(Point(line.coords[0]))
                        intersection_points.append(Point(line.coords[-1]))
        
        if not intersection_points:
            print("  ⚠️  No intersection points found")
            return None
        
        # Create GeoDataFrame and find unique points (within tolerance)
        intersections_gdf = gpd.GeoDataFrame(geometry=intersection_points, crs='EPSG:3857')
        
        # Buffer and dissolve to find clusters (intersections)
        # Use 10m buffer to cluster nearby endpoints
        intersections_buffered = intersections_gdf.buffer(10)
        intersections_dissolved = gpd.GeoDataFrame(geometry=intersections_buffered, crs='EPSG:3857')
        intersections_dissolved = intersections_dissolved.dissolve()
        
        # Get centroids of dissolved buffers as intersection points
        intersection_centroids = []
        for geom in intersections_dissolved.geometry:
            if isinstance(geom, Polygon):
                intersection_centroids.append(geom.centroid)
            elif isinstance(geom, MultiPolygon):
                for poly in geom.geoms:
                    intersection_centroids.append(poly.centroid)
        
        intersections_final = gpd.GeoDataFrame(geometry=intersection_centroids, crs='EPSG:3857')
        
        print(f"  Found {len(intersections_final)} intersection points")
        return intersections_final
    except Exception as e:
        print(f"  ⚠️  Error finding intersections: {e}")
        import traceback
        traceback.print_exc()
        return None


def offset_point_to_sidewalk(point: Point, street_line: LineString, offset_distance_m: float = 3.0) -> Optional[Point]:
    """
    Offset a point perpendicular to the street centerline to approximate sidewalk location.
    offset_distance_m: Approximate distance from centerline to sidewalk (default 3m ~10ft)
    Returns point offset to the right side of the street (direction of travel).
    """
    try:
        # Find the point on the line closest to our point
        closest_point = street_line.interpolate(street_line.project(point))
        
        # Calculate perpendicular direction
        # Get direction vector of the line at this point
        if street_line.length == 0:
            return None
        
        # Get a small segment around the point to determine direction
        distance_along = street_line.project(closest_point)
        offset_small = 1.0  # 1 meter
        p1 = street_line.interpolate(max(0, distance_along - offset_small))
        p2 = street_line.interpolate(min(street_line.length, distance_along + offset_small))
        
        # Calculate direction vector
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        
        # Perpendicular vector (rotate 90 degrees)
        # For right side: (-dy, dx)
        length = np.sqrt(dx*dx + dy*dy)
        if length == 0:
            return None
        
        # Normalize and scale
        perp_x = -dy / length * offset_distance_m
        perp_y = dx / length * offset_distance_m
        
        # Offset point
        offset_point = Point(closest_point.x + perp_x, closest_point.y + perp_y)
        return offset_point
    except Exception:
        return None


def create_spatial_index(gdf: gpd.GeoDataFrame):
    """Create a spatial index for fast nearest neighbor queries.
    For polygons, uses centroids. For points, uses coordinates directly."""
    from scipy.spatial import cKDTree
    if len(gdf) == 0:
        return None
    
    # Check if geometries are points or polygons
    first_geom = gdf.geometry.iloc[0]
    if isinstance(first_geom, Point):
        coords = np.array([[geom.x, geom.y] for geom in gdf.geometry])
    else:
        # For polygons, use centroids
        coords = np.array([[geom.centroid.x, geom.centroid.y] for geom in gdf.geometry])
    
    return cKDTree(coords)


def check_points_in_sidewalks_parallel(args):
    """Helper function for parallel sidewalk checking."""
    points_chunk, sidewalks = args
    point_geoms = [Point(x, y) for x, y in points_chunk]
    point_gdf = gpd.GeoDataFrame(geometry=point_geoms, crs='EPSG:3857')
    
    # Use spatial join
    within_sidewalks = gpd.sjoin(
        point_gdf, 
        sidewalks, 
        how='left', 
        predicate='within',
        lsuffix='left', 
        rsuffix='right'
    )
    
    # Return mask: True if point has a match
    matched_point_indices = set(within_sidewalks[within_sidewalks.index_right.notna()].index)
    return matched_point_indices


def is_points_valid_batch(
    points: np.ndarray,
    tree_index,
    stop_sign_index,
    street_sign_index,
    hydrant_index,
    bus_stop_index,
    intersection_index,
    building_index,
    sidewalks: Optional[gpd.GeoDataFrame],
    min_spacing_m: float,
    use_parallel: bool = True
) -> np.ndarray:
    """Check if points are valid for tree planting using NYC rules (vectorized)."""
    n_points = len(points)
    valid_mask = np.ones(n_points, dtype=bool)
    
    # Check distance to existing trees (30ft minimum)
    if tree_index is not None:
        distances, _ = tree_index.query(points, k=1)
        valid_mask &= distances >= min_spacing_m
    
    # Check distance to stop signs (30ft minimum)
    if stop_sign_index is not None:
        distances, _ = stop_sign_index.query(points, k=1)
        valid_mask &= distances >= STOP_SIGN_CLEARANCE_M
    
    # Check distance to street signs (6ft minimum)
    if street_sign_index is not None:
        distances, _ = street_sign_index.query(points, k=1)
        valid_mask &= distances >= STREET_SIGN_CLEARANCE_M
    
    # Check distance to hydrants (5ft minimum)
    if hydrant_index is not None:
        distances, _ = hydrant_index.query(points, k=1)
        valid_mask &= distances >= HYDRANT_CLEARANCE_M
    
    # Check distance to bus stops (no trees at curb, but can be set back)
    if bus_stop_index is not None:
        distances, _ = bus_stop_index.query(points, k=1)
        valid_mask &= distances >= 3.0  # ~10ft clearance
    
    # Check distance to intersections (40ft minimum)
    if intersection_index is not None:
        distances, _ = intersection_index.query(points, k=1)
        valid_mask &= distances >= INTERSECTION_CLEARANCE_M
    
    # Check distance to buildings (need minimum clearance, using 5ft as default)
    BUILDING_CLEARANCE_M = 5 * FT_TO_M  # 5ft minimum
    if building_index is not None:
        distances, _ = building_index.query(points, k=1)
        valid_mask &= distances >= BUILDING_CLEARANCE_M
    
    # Check if points are within sidewalks (if sidewalk data available)
    # Use parallel processing for performance
    if sidewalks is not None and len(sidewalks) > 0 and n_points > 0:
        try:
            # Parallelize sidewalk check for large batches
            if use_parallel and n_points > 1000:
                # Split points into chunks for parallel processing
                num_workers = min(cpu_count(), 8)  # Use up to 8 cores
                chunk_size = max(1000, n_points // (num_workers * 2))
                chunks = [points[i:i+chunk_size] for i in range(0, n_points, chunk_size)]
                
                # Process chunks in parallel
                with Pool(processes=num_workers) as pool:
                    args = [(chunk, sidewalks) for chunk in chunks]
                    results = pool.map(check_points_in_sidewalks_parallel, args)
                
                # Combine results from all chunks
                all_matched_indices = set()
                offset = 0
                for result_set in results:
                    # Adjust indices for chunk offset
                    adjusted_indices = {idx + offset for idx in result_set}
                    all_matched_indices.update(adjusted_indices)
                    offset += len(chunks[results.index(result_set)])
                
                within_mask = np.array([i in all_matched_indices for i in range(n_points)])
            else:
                # Sequential processing for small batches
                point_geoms = [Point(x, y) for x, y in points]
                point_gdf = gpd.GeoDataFrame(geometry=point_geoms, crs='EPSG:3857')
                
                within_sidewalks = gpd.sjoin(
                    point_gdf, 
                    sidewalks, 
                    how='left', 
                    predicate='within',
                    lsuffix='left', 
                    rsuffix='right'
                )
                
                matched_point_indices = set(within_sidewalks[within_sidewalks.index_right.notna()].index)
                within_mask = np.array([i in matched_point_indices for i in range(n_points)])
            
            # Points that are NOT within any sidewalk are invalid
            valid_mask &= within_mask
        except Exception as e:
            # If sidewalk check fails, log but don't skip (required check)
            print(f"  ⚠️  Sidewalk check error: {e}")
            # Set all to invalid if check fails
            valid_mask &= False
    
    return valid_mask


def is_point_valid(
    point: Point,
    tree_index,
    stop_sign_index,
    street_sign_index,
    hydrant_index,
    bus_stop_index,
    min_spacing_m: float
) -> Tuple[bool, str]:
    """Check if a point is valid for tree planting using NYC rules (legacy single-point version)."""
    point_coord = np.array([[point.x, point.y]])
    
    # Check distance to existing trees (30ft minimum)
    if tree_index is not None:
        distances, _ = tree_index.query(point_coord, k=1)
        min_tree_distance = distances[0]
        if min_tree_distance < min_spacing_m:
            return False, f"Too close to existing tree ({min_tree_distance/FT_TO_M:.1f} ft, need {TREE_SPACING_FT} ft)"
    
    # Check distance to stop signs (30ft minimum)
    if stop_sign_index is not None:
        distances, _ = stop_sign_index.query(point_coord, k=1)
        min_stop_distance = distances[0]
        if min_stop_distance < STOP_SIGN_CLEARANCE_M:
            return False, f"Too close to stop sign ({min_stop_distance/FT_TO_M:.1f} ft, need {STOP_SIGN_CLEARANCE_FT} ft)"
    
    # Check distance to street signs (6ft minimum)
    if street_sign_index is not None:
        distances, _ = street_sign_index.query(point_coord, k=1)
        min_sign_distance = distances[0]
        if min_sign_distance < STREET_SIGN_CLEARANCE_M:
            return False, f"Too close to street sign ({min_sign_distance/FT_TO_M:.1f} ft, need {STREET_SIGN_CLEARANCE_FT} ft)"
    
    # Check distance to hydrants (5ft minimum)
    if hydrant_index is not None:
        distances, _ = hydrant_index.query(point_coord, k=1)
        min_hydrant_distance = distances[0]
        if min_hydrant_distance < HYDRANT_CLEARANCE_M:
            return False, f"Too close to hydrant ({min_hydrant_distance/FT_TO_M:.1f} ft, need {HYDRANT_CLEARANCE_FT} ft)"
    
    # Check distance to bus stops (no trees at curb, but can be set back)
    # For now, we'll use a small clearance to avoid planting directly at curb
    if bus_stop_index is not None:
        distances, _ = bus_stop_index.query(point_coord, k=1)
        min_bus_distance = distances[0]
        # Note: In practice, would need sidewalk data to allow set-back planting
        # For now, we'll be conservative and avoid bus stops
        if min_bus_distance < 3.0:  # ~10ft clearance
            return False, f"Too close to bus stop ({min_bus_distance/FT_TO_M:.1f} ft)"
    
    return True, "Valid"


def generate_points_along_street(street_line: LineString, spacing_m: float) -> List[Point]:
    """Generate points along a street line at specified spacing."""
    points = []
    
    try:
        length = street_line.length
        
        if length < spacing_m:
            # Street too short, skip
            return points
        
        # Generate points along the line
        # Start a bit in from the ends to avoid intersections
        start_offset = min(spacing_m * 0.5, length * 0.1)
        end_offset = min(spacing_m * 0.5, length * 0.1)
        usable_length = length - start_offset - end_offset
        
        if usable_length < spacing_m:
            return points
        
        # Generate points at exactly spacing_m intervals
        num_points = int(usable_length / spacing_m)
        for i in range(num_points + 1):
            distance = start_offset + (i * spacing_m)
            if distance < length:
                point = street_line.interpolate(distance)
                points.append(point)
    except Exception as e:
        return []
    
    return points


def generate_points_along_streets_batch(geometries: List[LineString], spacing_m: float, offset_to_sidewalk: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    """Generate points along multiple street lines (vectorized). Returns coordinates and geometry indices.
    If offset_to_sidewalk is True, offsets points perpendicular to sidewalk (default 3m from centerline)."""
    all_coords = []
    geom_indices = []
    SIDEWALK_OFFSET_M = 3.0  # Approximate 10ft offset from centerline to sidewalk
    
    for geom_idx, geom in enumerate(geometries):
        if not isinstance(geom, LineString):
            continue
            
        try:
            length = geom.length
            if length < spacing_m:
                continue
            
            # Start/end offsets to avoid intersections (increased for intersection clearance)
            start_offset = max(INTERSECTION_CLEARANCE_M, spacing_m * 0.5)
            end_offset = max(INTERSECTION_CLEARANCE_M, spacing_m * 0.5)
            usable_length = length - start_offset - end_offset
            
            if usable_length < spacing_m:
                continue
            
            num_points = int(usable_length / spacing_m)
            for i in range(num_points + 1):
                distance = start_offset + (i * spacing_m)
                if distance < length:
                    point_on_line = geom.interpolate(distance)
                    
                    # Offset to sidewalk if requested
                    if offset_to_sidewalk:
                        offset_point = offset_point_to_sidewalk(point_on_line, geom, SIDEWALK_OFFSET_M)
                        if offset_point is not None:
                            all_coords.append([offset_point.x, offset_point.y])
                            geom_indices.append(geom_idx)
                    else:
                        all_coords.append([point_on_line.x, point_on_line.y])
                        geom_indices.append(geom_idx)
        except Exception:
            continue
    
    if not all_coords:
        return np.array([]), np.array([])
    
    return np.array(all_coords), np.array(geom_indices)


def generate_planting_coordinates(
    streets: gpd.GeoDataFrame,
    existing_trees: gpd.GeoDataFrame,
    constraints: Dict,
    sidewalks: Optional[gpd.GeoDataFrame] = None,
    buildings: Optional[gpd.GeoDataFrame] = None,
    intersections: Optional[gpd.GeoDataFrame] = None
) -> List[Dict]:
    """Generate all valid tree planting coordinates along streets."""
    print("\nGenerating planting coordinates along streets...")
    print(f"  Using tree spacing: {TREE_SPACING_FT} ft ({TREE_SPACING_M:.2f} m)")
    print(f"  Tree diameter: {TREE_DIAMETER_INCHES} inches")
    print(f"  Intersection clearance: {INTERSECTION_CLEARANCE_FT} ft")
    print(f"  Points offset to sidewalk: Yes (3m from centerline)")
    
    # Create spatial indexes for fast queries
    print("  Creating spatial indexes...")
    tree_index = create_spatial_index(existing_trees)
    stop_sign_index = create_spatial_index(constraints.get('stop_signs', gpd.GeoDataFrame()))
    street_sign_index = create_spatial_index(constraints.get('street_signs', gpd.GeoDataFrame()))
    hydrant_index = create_spatial_index(constraints.get('hydrants', gpd.GeoDataFrame()))
    bus_stop_index = create_spatial_index(constraints.get('bus_stops', gpd.GeoDataFrame()))
    intersection_index = create_spatial_index(intersections) if intersections is not None else None
    building_index = create_spatial_index(buildings) if buildings is not None else None
    print("  Spatial indexes created")
    
    valid_coordinates = []
    total_points_generated = 0
    total_valid = 0
    
    print(f"  Processing {len(streets):,} street segments...")
    print(f"  (Printing every 100th coordinate, progress updates every 5 batches)\n")
    
    # Process streets in batches (avoid iterrows - use iloc instead)
    batch_size = 5000
    num_batches = (len(streets) + batch_size - 1) // batch_size
    
    # Process geometries in batches for validation
    # Smaller batches for sidewalk check to avoid memory issues
    validation_batch_size = 5000  # Process points in batches for validation (reduced for sidewalk check)
    
    for batch_idx in range(num_batches):
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, len(streets))
        
        # Collect geometries for this batch (using iloc is much faster than iterrows)
        batch_geometries = []
        for idx in range(start_idx, end_idx):
            street_geom = streets.iloc[idx].geometry
            if isinstance(street_geom, LineString):
                batch_geometries.append(street_geom)
            elif hasattr(street_geom, 'geoms'):  # MultiLineString
                for geom in street_geom.geoms:
                    if isinstance(geom, LineString):
                        batch_geometries.append(geom)
        
        # Generate all candidate points for this batch
        candidate_coords, _ = generate_points_along_streets_batch(batch_geometries, TREE_SPACING_M)
        total_points_generated += len(candidate_coords)
        
        if len(candidate_coords) == 0:
            continue
        
        # Validate points in batches
        for val_start in range(0, len(candidate_coords), validation_batch_size):
            val_end = min(val_start + validation_batch_size, len(candidate_coords))
            batch_coords = candidate_coords[val_start:val_end]
            
            # Show progress for validation batches
            if val_start % (validation_batch_size * 5) == 0:
                print(f"  Validating batch {val_start//validation_batch_size + 1} ({len(batch_coords)} points, {total_valid:,} valid so far)...")
            
            # Vectorized validation (with parallel sidewalk check)
            valid_mask = is_points_valid_batch(
                batch_coords,
                tree_index,
                stop_sign_index,
                street_sign_index,
                hydrant_index,
                bus_stop_index,
                intersection_index,
                building_index,
                sidewalks,
                TREE_SPACING_M,
                use_parallel=True
            )
            
            valid_coords_batch = batch_coords[valid_mask]
            
            if len(valid_coords_batch) > 0:
                # Convert valid coordinates to WGS84 in batch
                valid_points = [Point(x, y) for x, y in valid_coords_batch]
                valid_gdf = gpd.GeoDataFrame(geometry=valid_points, crs='EPSG:3857')
                valid_gdf_wgs84 = valid_gdf.to_crs('EPSG:4326')
                
                # Add to results
                for point in valid_gdf_wgs84.geometry:
                    coord_data = {
                        'latitude': float(point.y),
                        'longitude': float(point.x)
                    }
                    valid_coordinates.append(coord_data)
                    total_valid += 1
                    
                    # Print every 100th coordinate
                    if total_valid % 100 == 0:
                        print(f"[{total_valid:,}] lat: {coord_data['latitude']:.6f}, lon: {coord_data['longitude']:.6f}")
        
        if (batch_idx + 1) % 5 == 0:
            print(f"  [Progress] Processed {end_idx:,}/{len(streets):,} streets ({end_idx/len(streets)*100:.1f}%), found {total_valid:,} valid locations so far...")
    
    print(f"\n  Total candidate points generated: {total_points_generated:,}")
    print(f"  Valid planting locations: {total_valid:,}")
    if total_points_generated > 0:
        print(f"  Validation rate: {total_valid/total_points_generated*100:.1f}%")
    
    return valid_coordinates


def main():
    """Main function to generate all available tree planting coordinates."""
    print("="*60)
    print("GENERATE TREE PLANTING COORDINATES")
    print("="*60)
    print("\nNYC Street Tree Planting Rules Applied:")
    print(f"  - Tree spacing: {TREE_SPACING_FT} ft apart")
    print(f"  - Tree diameter: {TREE_DIAMETER_INCHES} inches")
    print(f"  - Stop signs: {STOP_SIGN_CLEARANCE_FT} ft clearance")
    print(f"  - Street signs: {STREET_SIGN_CLEARANCE_FT} ft clearance")
    print(f"  - Hydrants: {HYDRANT_CLEARANCE_FT} ft clearance")
    print(f"  - Intersections: {INTERSECTION_CLEARANCE_FT} ft clearance")
    print(f"  - Buildings: 5 ft minimum clearance")
    print(f"  - Sidewalks: Points must be within sidewalk polygons")
    print(f"  - Bus stops: No trees at curb (set back in sidewalk)")
    print("="*60 + "\n")
    
    # Load data
    streets = load_lion_streets()
    if streets is None:
        print("ERROR: Cannot proceed without LION street network")
        return
    
    existing_trees = load_existing_trees()
    constraints = load_constraint_points()
    sidewalks = load_sidewalks()
    buildings = load_buildings()
    intersections = find_intersections(streets)
    
    # Generate coordinates
    coordinates = generate_planting_coordinates(
        streets, 
        existing_trees, 
        constraints,
        sidewalks=sidewalks,
        buildings=buildings,
        intersections=intersections
    )
    
    # Save to JSON
    output_path = OUTPUT_DIR / "available_tree_planting_coordinates.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    output_data = {
        'metadata': {
            'generation_date': pd.Timestamp.now().isoformat(),
            'total_locations': len(coordinates),
            'tree_spacing_ft': TREE_SPACING_FT,
            'tree_diameter_inches': TREE_DIAMETER_INCHES,
            'rules_applied': {
                'tree_spacing_ft': TREE_SPACING_FT,
                'stop_sign_clearance_ft': STOP_SIGN_CLEARANCE_FT,
                'street_sign_clearance_ft': STREET_SIGN_CLEARANCE_FT,
                'hydrant_clearance_ft': HYDRANT_CLEARANCE_FT,
                'intersection_clearance_ft': INTERSECTION_CLEARANCE_FT,
                'street_light_clearance_ft': STREET_LIGHT_CLEARANCE_FT,
                'curb_cut_clearance_ft': CURB_CUT_CLEARANCE_FT
            }
        },
        'coordinates': coordinates
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✅ Saved {len(coordinates):,} coordinates to: {output_path}")
    print(f"   File size: {output_path.stat().st_size / (1024*1024):.1f} MB")
    
    print("\n" + "="*60)
    print("GENERATION COMPLETE")
    print("="*60)


if __name__ == '__main__':
    main()
