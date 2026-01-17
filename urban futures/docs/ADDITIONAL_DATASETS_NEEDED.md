# Additional Datasets Needed for Accurate Planting Location Analysis

## Current Status

✅ **Already Have:**
- 2015 Street Tree Census (652,173 trees)
- Parking Regulation Locations and Signs (404,262 signs)
- Street Sign Work Orders (45,493 work orders)
- Building Footprints (sampled 50k from 514MB file)

## Critical Missing Datasets

### 1. **Street Network / Road Centerlines** ⭐⭐⭐⭐⭐
**Priority: CRITICAL**

**Dataset:** LION (Line of Interest Network) - NYC Planning
- **What it provides:** Street centerlines, road classifications, street widths
- **Why needed:** Without this, we don't know where streets actually are. Current analysis only looks at tree-to-tree distances, not actual street locations.
- **Source:** 
  - NYC Planning: https://www.nyc.gov/site/planning/data-maps/open-data/dwn-lion.page
  - NYC Open Data: https://data.cityofnewyork.us/City-Government/LION/ (may be available)
- **File format:** Shapefile (.shp) or GeoJSON
- **Use case:** 
  - Identify actual street locations
  - Calculate planting locations along street centerlines
  - Determine street width and classification
  - Filter to public right-of-way only

**Impact:** Without this, we can't determine actual planting locations - only theoretical spacing.

---

### 2. **Sidewalk Data** ⭐⭐⭐⭐⭐
**Priority: CRITICAL**

**Dataset:** NYC Planimetric Database - Sidewalk
- **What it provides:** Sidewalk polygons, widths, locations
- **Why needed:** Trees are planted in the space between sidewalk and curb. Need to know where sidewalks are and their width.
- **Source:** 
  - NYC Open Data: https://data.cityofnewyork.us/City-Government/Sidewalk/vfx9-tbb6
  - Alternative: Sidewalk Widths NYC: https://sidewalkwidths.nyc/
- **File format:** Shapefile or GeoJSON
- **Use case:**
  - Identify planting strip locations (between curb and sidewalk)
  - Verify minimum planting strip width (typically 3-5 ft minimum)
  - Calculate available planting area

**Impact:** Without this, we can't verify if there's enough space for tree planting.

---

### 3. **Curb / Street Edge Data** ⭐⭐⭐⭐
**Priority: HIGH**

**Dataset:** NYC Planimetric Database - Curb
- **What it provides:** Curb line locations
- **Why needed:** Trees are typically planted between curb and sidewalk. Need to know where curbs are.
- **Source:** NYC Planimetric Database (part of NYC Planning's planimetric data)
- **File format:** Shapefile or GeoJSON
- **Use case:**
  - Define planting strip boundaries (curb to sidewalk)
  - Calculate planting strip width
  - Identify areas where trees can be planted

**Impact:** Needed to accurately define planting locations.

---

### 4. **Public Right-of-Way (ROW) Boundaries** ⭐⭐⭐⭐⭐
**Priority: CRITICAL**

**Dataset:** Public Right-of-Way boundaries / Property boundaries
- **What it provides:** Boundaries between public and private property
- **Why needed:** Trees can ONLY be planted in public right-of-way, not on private property.
- **Source:** 
  - NYC Planning PLUTO dataset (includes property boundaries)
  - NYC DOT Right-of-Way data
- **File format:** Shapefile or GeoJSON
- **Use case:**
  - Filter out private property
  - Identify public spaces where trees can be planted
  - Calculate available public space

**Impact:** Without this, we may be counting locations on private property where trees can't be planted.

---

### 5. **Street Width / Curb-to-Curb Width** ⭐⭐⭐⭐
**Priority: HIGH**

**Dataset:** Street width measurements or cross-section data
- **What it provides:** Actual street width, curb-to-curb distance
- **Why needed:** Narrow streets may not accommodate trees even with adequate spacing. Need to know if there's enough room.
- **Source:** 
  - LION dataset (may include width)
  - NYC DOT street width data
  - Calculated from planimetric data (curb to curb)
- **File format:** Shapefile with width attribute or separate dataset
- **Use case:**
  - Filter out streets too narrow for tree planting
  - Determine planting strip width
  - Calculate available space

**Impact:** Prevents counting locations on streets that are too narrow.

---

### 6. **Infrastructure / Obstruction Data** ⭐⭐⭐⭐
**Priority: HIGH**

**Datasets:**
- **Fire Hydrants:** Location of all fire hydrants
- **Street Furniture:** Lampposts, benches, bus stops, bike racks
- **Utility Vaults:** Manholes, utility access points
- **Traffic Signals:** Traffic light poles
- **Bus Stops:** Bus stop locations and shelters

**Why needed:** These obstructions prevent tree planting at specific locations.

**Sources:**
- NYC Open Data: Various infrastructure datasets
- NYC DOT: Street furniture locations
- MTA: Bus stop locations

**Use case:**
- Identify locations where trees cannot be planted
- Subtract obstructed areas from available locations
- Calculate actual available space

**Impact:** Significantly reduces available locations (may reduce count by 10-20%).

---

### 7. **Underground Utilities** ⭐⭐⭐
**Priority: MEDIUM**

**Datasets:**
- Water mains
- Sewer lines
- Gas lines
- Steam lines
- Electrical conduits
- Subway tunnels

**Why needed:** NYC design manuals require avoiding planting trees directly over underground utilities, especially water/sewer mains.

**Sources:**
- NYC DEP: Water and sewer data
- Con Edison: Gas and electrical data
- MTA: Subway tunnel data

**Use case:**
- Identify areas where trees cannot be planted (over utilities)
- Calculate setbacks from utility lines
- Filter out constrained locations

**Impact:** May reduce available locations by 5-10%.

---

### 8. **Intersection / Sightline Data** ⭐⭐⭐
**Priority: MEDIUM**

**Dataset:** Intersection locations and sightline setback zones
- **What it provides:** Areas near intersections where trees must be set back (typically 35 ft from intersecting curb)
- **Why needed:** Legal requirement to avoid blocking visibility at intersections
- **Source:** 
  - LION dataset (includes intersection nodes)
  - Calculated from street network
- **Use case:**
  - Identify intersection setback zones
  - Filter out locations too close to intersections
  - Calculate available space excluding setbacks

**Impact:** May reduce available locations by 5-10% near intersections.

---

### 9. **Pedestrian Ramps / Curb Ramps** ⭐⭐⭐
**Priority: MEDIUM**

**Dataset:** NYC Pedestrian Ramps Survey
- **What it provides:** Location of ADA-compliant curb ramps
- **Why needed:** Tree planting may interfere with ramp geometry or ADA access
- **Source:** 
  - NYC Pedestrian Ramps: https://www.nycpedramps.info/survey
  - NYC Open Data (may be available)
- **Use case:**
  - Identify locations near ramps where trees may not be suitable
  - Ensure ADA compliance
  - Calculate available space excluding ramp areas

**Impact:** Small impact, but important for ADA compliance.

---

### 10. **Street Classification / Traffic Volume** ⭐⭐
**Priority: LOW**

**Dataset:** Street classification (local, collector, arterial) and traffic volume
- **What it provides:** Street type and traffic levels
- **Why needed:** Some streets may have restrictions or require different spacing due to traffic
- **Source:** 
  - LION dataset (includes street classification)
  - NYC DOT traffic volume data
- **Use case:**
  - Apply different rules for different street types
  - Identify streets with special restrictions
  - Prioritize planting on appropriate street types

**Impact:** Minor impact, but helps refine estimates.

---

### 11. **Tree Species / Approved Species List** ⭐⭐
**Priority: LOW**

**Dataset:** NYC Parks approved street tree species and mature canopy widths
- **What it provides:** List of approved species and their mature sizes
- **Why needed:** Spacing requirements depend on species (some need more space)
- **Source:** 
  - NYC Parks: https://www.nycgovparks.org/trees/street-tree-planting/species-list
  - Can be manually compiled
- **Use case:**
  - Apply species-specific spacing rules
  - Calculate appropriate spacing based on mature canopy width
  - Filter species by street type/width

**Impact:** Minor impact, but helps with species selection.

---

## Priority Ranking

### Must Have (Cannot proceed without):
1. ⭐⭐⭐⭐⭐ **Street Network / LION** - Need to know where streets are
2. ⭐⭐⭐⭐⭐ **Sidewalk Data** - Need to know where planting strips are
3. ⭐⭐⭐⭐⭐ **Public Right-of-Way Boundaries** - Need to filter out private property

### Should Have (Significantly improves accuracy):
4. ⭐⭐⭐⭐ **Curb Data** - Define planting strip boundaries
5. ⭐⭐⭐⭐ **Street Width Data** - Filter out narrow streets
6. ⭐⭐⭐⭐ **Infrastructure / Obstruction Data** - Account for physical constraints

### Nice to Have (Refines estimates):
7. ⭐⭐⭐ **Underground Utilities** - Avoid utility conflicts
8. ⭐⭐⭐ **Intersection / Sightline Data** - Legal requirements
9. ⭐⭐⭐ **Pedestrian Ramps** - ADA compliance
10. ⭐⭐ **Street Classification** - Apply appropriate rules
11. ⭐⭐ **Tree Species Data** - Species-specific spacing

## Estimated Impact on Count

With current data: **~415,433 locations** (theoretical maximum)

With critical datasets (LION + Sidewalk + ROW):
- **Expected reduction:** 30-50% (removes private property, non-street locations)
- **New estimate:** ~200,000-290,000 locations

With all recommended datasets:
- **Expected reduction:** 40-60% (accounts for all constraints)
- **Final estimate:** ~165,000-250,000 locations

## Next Steps

1. **Download LION dataset** (highest priority)
2. **Download Sidewalk data** (highest priority)
3. **Download Public ROW boundaries** (highest priority)
4. **Re-run analysis** with street network data
5. **Add infrastructure data** to refine estimates
6. **Integrate results** into H3 feature calculation

## Data Sources Summary

| Dataset | Source | Format | Priority |
|---------|--------|--------|----------|
| LION (Street Network) | NYC Planning | Shapefile | ⭐⭐⭐⭐⭐ |
| Sidewalk | NYC Open Data | Shapefile/GeoJSON | ⭐⭐⭐⭐⭐ |
| Public ROW | NYC Planning PLUTO | Shapefile | ⭐⭐⭐⭐⭐ |
| Curb | NYC Planimetric DB | Shapefile | ⭐⭐⭐⭐ |
| Street Width | LION or calculated | Attribute/Shapefile | ⭐⭐⭐⭐ |
| Fire Hydrants | NYC Open Data | CSV/Shapefile | ⭐⭐⭐⭐ |
| Bus Stops | MTA / NYC Open Data | CSV/Shapefile | ⭐⭐⭐⭐ |
| Utilities | Various agencies | Shapefile | ⭐⭐⭐ |
| Intersections | LION (calculated) | Shapefile | ⭐⭐⭐ |
| Pedestrian Ramps | NYC Ped Ramps | CSV/Shapefile | ⭐⭐⭐ |

## Notes

- **LION dataset is the most critical** - without it, we can't determine actual planting locations
- **Many datasets may be available through NYC Open Data portal** - check https://data.cityofnewyork.us/
- **Some data may need to be requested** from specific agencies (NYC DOT, DEP, etc.)
- **Consider data licensing** - ensure you can use the data for your purposes
- **Data updates** - some datasets are updated regularly, others are static
