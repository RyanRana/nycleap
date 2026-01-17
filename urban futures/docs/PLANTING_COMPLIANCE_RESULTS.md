# Street Tree Planting Compliance Analysis - Results

## Summary

Based on NYC street tree planting compliance rules, we can estimate **~415,433 legally available street tree planting locations** across New York City.

This represents a **63.7% potential increase** over the current tree count of 652,173 trees.

## Analysis Date

January 16, 2026

## Compliance Rules Applied

1. **Tree-to-tree spacing**: 20-30 ft (nearest neighbor)
2. **Stop signs**: ≥ 30 ft clearance
3. **Other traffic signs**: ≥ 6 ft clearance
4. **Building clearance**: Distance to nearest building footprint edge

## Detailed Results

### Tree Spacing Analysis

- **Total existing trees**: 652,173
- **Trees with spacing < 20 ft** (too close, violations): 41,202
- **Trees with spacing 20-30 ft** (optimal): 128,075
- **Trees with spacing > 30 ft** (can plant nearby): 482,896
- **Average nearest neighbor distance**: 42.6 ft

### Sign Constraints

- **Parking regulation signs**: 404,262 signs
  - **Identified stop signs**: 17,872
  - **Trees within 6 ft of signs** (violations): 5,559
  - **Trees within 30 ft of stop signs** (violations): 3,321

- **Street sign work orders**: 45,493 work orders
  - **Additional trees within 6 ft**: 401

- **Total sign-constrained areas**: 449,755

### Building Constraints

- **Average distance to nearest building**: 276.7 ft
- **Trees within 3 ft of buildings** (violations): 0
- **Trees with adequate clearance**: 652,173 (100%)

### Estimated Available Locations

- **Base estimate** (from spacing gaps): 482,896 locations
- **Sign constraint penalty**: -67,463 locations
- **Building constraint penalty**: -0 locations
- **──────────────────────────────────────────────**
- **ESTIMATED LEGALLY AVAILABLE**: **415,433 locations**
- **──────────────────────────────────────────────**

- **Alternative estimate** (by block): ~60,000 locations
- **Potential increase**: 63.7% of current tree count

## Important Limitations

⚠️ **This analysis has several limitations:**

1. **No road centerlines**: The analysis doesn't know where streets actually are. It only analyzes tree-to-tree distances, not actual street layout. Without street network data, we cannot determine exact planting locations.

2. **Sign data is a proxy**: 
   - Parking regulation signs cover many sign locations but may not be complete
   - Street sign work orders are maintenance-based, not a complete inventory
   - Stop sign identification is based on keyword matching in descriptions

3. **Building clearance is approximate**: 
   - Uses building centroids as a proxy (not actual building edge distances)
   - Cannot detect stoops/railings citywide
   - Distance calculation is to building center, not edge

4. **Street width unknown**: Actual planting capacity depends on street width. Narrow streets may not accommodate trees even if spacing allows.

5. **Public vs private**: The analysis doesn't distinguish between public right-of-way (where street trees can be planted) and private property.

6. **Infrastructure**: Utilities, sidewalks, and other infrastructure may further constrain planting locations.

7. **Compliance data doesn't include roads**: As noted, the compliance datasets don't include road centerlines or street networks, which are essential for determining actual planting locations.

## What This Means

The estimate of **~415,433 available locations** is based on:
- Tree spacing gaps (482,896 potential sites)
- Adjusted for sign constraints (-67,463 sites)

However, **this is a theoretical maximum**. The actual number of legally plantable trees will be lower because:

1. **Street layout matters**: Trees must be planted along actual streets, not just anywhere with adequate spacing
2. **Street width varies**: Narrow streets may not accommodate trees even with adequate spacing
3. **Infrastructure conflicts**: Utilities, fire hydrants, bus stops, etc. further constrain locations
4. **Public right-of-way only**: Trees can only be planted in public spaces, not on private property

## Recommendations

To get a more accurate count:

1. **Add street network data**: Use NYC Planning's LION (Line of Interest Network) dataset to identify actual street centerlines
2. **Add street width data**: Use street width information to determine actual planting capacity
3. **Filter by public right-of-way**: Use property data to identify public vs private areas
4. **Add infrastructure data**: Include utilities, fire hydrants, bus stops, etc. in the analysis
5. **Use actual building edges**: Calculate distance to actual building footprint edges, not centroids

## Next Steps

1. ✅ **Completed**: Tree spacing analysis
2. ✅ **Completed**: Sign constraint analysis (with available data)
3. ✅ **Completed**: Building clearance analysis (approximate)
4. ⏳ **Pending**: Integrate street network data (LION dataset)
5. ⏳ **Pending**: Add street width constraints
6. ⏳ **Pending**: Filter by public right-of-way
7. ⏳ **Pending**: Integrate results into H3 feature calculation
8. ⏳ **Pending**: Display available locations on the map

## Files Generated

- `data/processed/available_planting_locations.json` - Detailed analysis results
- `python/data_pipeline/calculate_available_planting_locations.py` - Analysis script

## Running the Analysis

```bash
cd python/data_pipeline
python3 calculate_available_planting_locations.py
```

## Data Sources Used

1. **2015 Street Tree Census** (`street_trees_2015.csv`)
   - 652,173 alive trees
   - Source: https://data.cityofnewyork.us/Environment/2015-Street-Tree-Census-Tree-Data/uvpi-gqnh

2. **Parking Regulation Locations and Signs** (`Parking_Regulation_Locations_and_Signs_20260116.csv`)
   - 404,262 signs
   - Source: https://data.cityofnewyork.us/City-Government/Parking-Regulation-Locations-and-Signs/nfid-uabd

3. **Street Sign Work Orders** (`Street_Sign_Work_Orders_20260116.csv`)
   - 45,493 work orders (sampled 100k rows from 3GB file)
   - Source: https://data.cityofnewyork.us/City-Government/Street-Sign-Work-Orders/qt6m-xctn

4. **Building Footprints** (`BUILDING_20260116.csv`)
   - 50,000 buildings (sampled from 514MB file)
   - Source: https://data.cityofnewyork.us/Housing-Development/Building-Footprints/5zhs-2jue
