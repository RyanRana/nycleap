# Street Tree Planting Compliance Analysis

This document explains how to calculate legally available street tree planting locations based on NYC's street tree planting compliance rules.

## Compliance Rules

1. **Tree-to-tree spacing**: 20-30 ft (nearest neighbor)
2. **Stop signs**: ≥ 30 ft clearance
3. **Other traffic signs**: ≥ 6 ft clearance  
4. **Building clearance**: Distance to nearest building footprint edge

## Running the Analysis

```bash
cd python/data_pipeline
python3 calculate_available_planting_locations.py
```

## Required Datasets

### Already Available
- ✅ **2015 Street Tree Census** (`street_trees_2015.csv`)
  - Used for: Tree-to-tree spacing analysis
  - Source: https://data.cityofnewyork.us/Environment/2015-Street-Tree-Census-Tree-Data/uvpi-gqnh

### Need to Download

1. **Parking Regulation Locations and Signs** (Dataset ID: `nfid-uabd`)
   - **Download**: https://data.cityofnewyork.us/City-Government/Parking-Regulation-Locations-and-Signs/nfid-uabd
   - **Save as**: `data/cache/parking_regulation_signs.csv`
   - **Use**: Traffic sign clearance (≥ 6 ft), proxy for stop signs (≥ 30 ft)

2. **Street Sign Work Orders** (Dataset ID: `qt6m-xctn`)
   - **Download**: https://data.cityofnewyork.us/City-Government/Street-Sign-Work-Orders/qt6m-xctn
   - **Save as**: `data/cache/street_sign_work_orders.csv`
   - **Use**: Additional sign locations (work-order based, not complete inventory)

3. **Building Footprints** (Dataset ID: `5zhs-2jue`)
   - **Download**: https://data.cityofnewyork.us/Housing-Development/Building-Footprints/5zhs-2jue
   - **Save as**: `data/cache/buildings.csv` or `data/external/buildings/buildings.shp`
   - **Use**: Building clearance calculations (distance to nearest building edge)

## Current Results (Based on Tree Spacing Only)

Based on the 2015 Street Tree Census analysis:

- **Total existing trees**: 652,173
- **Trees with spacing < 20 ft** (too close, violations): 41,202
- **Trees with spacing 20-30 ft** (optimal): 128,075
- **Trees with spacing > 30 ft** (can plant nearby): 482,896
- **Average nearest neighbor distance**: 42.6 ft

**Estimated legally available locations**: ~482,896 (based on spacing gaps)

**Potential increase**: ~74% of current tree count

## Limitations

⚠️ **Important**: This analysis has several limitations:

1. **No road centerlines**: The analysis doesn't know where streets actually are. It only analyzes tree-to-tree distances, not actual street layout.

2. **Sign data missing**: Without parking regulation signs and street sign work orders, we cannot calculate sign clearance constraints. The estimate is based on spacing only.

3. **Building data missing**: Without building footprints, we cannot calculate building clearance. This is a proxy constraint anyway (we can't detect stoops/railings citywide).

4. **Street width unknown**: Actual planting capacity depends on street width. Narrow streets may not accommodate trees even if spacing allows.

5. **Public vs private**: The analysis doesn't distinguish between public right-of-way (where street trees can be planted) and private property.

6. **Infrastructure**: Utilities, sidewalks, and other infrastructure may further constrain planting locations.

## Improving the Analysis

To get more accurate estimates:

1. **Download sign datasets**: Add parking regulation signs and street sign work orders
2. **Download building footprints**: Add building clearance calculations
3. **Add street centerlines**: Use NYC Planning's LION (Line of Interest Network) dataset to identify actual street locations
4. **Add street width data**: Use street width information to determine actual planting capacity
5. **Filter by public right-of-way**: Use property data to identify public vs private areas

## Output

The script generates:
- `data/processed/available_planting_locations.json` - Detailed analysis results

## Next Steps

1. Download the missing datasets (signs, buildings)
2. Re-run the analysis with complete data
3. Integrate results into the H3 feature calculation
4. Add "legally available planting locations" as a feature in the priority score
5. Display available locations on the map

## Integration with Priority Score

Once calculated, the number of legally available planting locations per H3 cell can be:
- Added as a feature in the priority score calculation
- Displayed in the sidebar when clicking an H3 cell
- Used to refine recommended tree counts (don't recommend more than legally available)
