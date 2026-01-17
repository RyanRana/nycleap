# Critical Issues with Tree Planting Coordinates Generation

## 🚨 **MAJOR PROBLEM: 2.2 Million Trees is Unrealistic**

The current code generates **2,208,773 planting locations**, which is unrealistic. Here's why and what's missing:

---

## ❌ **CRITICAL ISSUES**

### 1. **Points are on STREET CENTERLINES, not sidewalks!**
- **Problem:** LION data provides street **centerlines**, but trees are planted on **sidewalks** (typically 2-3 feet from the curb)
- **Current behavior:** Code generates points directly on the street centerline
- **Impact:** All coordinates are in the middle of streets, not plantable locations
- **Fix needed:** Offset points perpendicular to street centerline to sidewalk location

### 2. **Sidewalk Data Exists But Is NOT Used**
- **Available data:** `NYC_Planimetric_Database__Sidewalk_20260116.csv` (50,867 rows)
- **Problem:** Code never loads or checks sidewalk data
- **Impact:** No verification that sidewalks actually exist at these locations
- **Fix needed:** Load sidewalk polygons and verify planting locations are within sidewalk areas

### 3. **Building Data Exists But Is NOT Used**
- **Available data:** `BUILDING_20260116.csv` 
- **Problem:** Code never loads or checks building proximity
- **Impact:** Trees could be placed too close to buildings (need clearance)
- **Fix needed:** Load building footprints and check minimum clearance distance

### 4. **Constraints Defined But NOT Implemented**

The following constraints are **defined** in the code but **never actually checked**:

| Constraint | Defined Value | Status | Impact |
|-----------|--------------|--------|--------|
| `INTERSECTION_CLEARANCE_FT` | 40 ft | ❌ Not checked | Trees too close to intersections |
| `STREET_LIGHT_CLEARANCE_FT` | 25 ft | ❌ Not checked | Trees too close to street lights |
| `CURB_CUT_CLEARANCE_FT` | 7 ft | ❌ Not checked | Trees blocking curb cuts (ADA violations) |
| `SIDEWALK_MIN_WIDTH_FT` | 3.25 ft | ❌ Not checked | Trees in narrow sidewalks |
| Building clearance | Not defined | ❌ Not checked | Trees too close to buildings |
| Utility clearances | Defined | ❌ Not checked | Conflicts with utilities |

### 5. **No Verification of Plantable Space**
- **Problem:** Code doesn't verify:
  - Is there actually a sidewalk at this location?
  - Is the sidewalk wide enough?
  - Is there a planting strip (space between curb and sidewalk)?
  - Is the location in a median (different rules apply)?

### 6. **Double Counting Potential**
- **Problem:** If streets have sidewalks on both sides, the code might be generating points for both sides without distinction
- **Impact:** Inflated count if not properly handled

---

## 📊 **What the Code IS Checking (Correctly)**

✅ Distance to existing trees (30ft minimum)  
✅ Distance to stop signs (30ft minimum)  
✅ Distance to street signs (6ft minimum)  
✅ Distance to hydrants (5ft minimum)  
✅ Distance to bus stops (~10ft clearance)  

---

## 🔧 **Required Fixes**

### Priority 1: CRITICAL
1. **Offset points from centerline to sidewalk** - Trees must be on sidewalks, not in streets
2. **Load and use sidewalk data** - Verify locations are actually on sidewalks
3. **Load and use building data** - Check building clearances
4. **Implement intersection clearance** - 40ft from intersections

### Priority 2: HIGH
5. **Implement street light clearance** - 25ft from street lights
6. **Implement curb cut clearance** - 7ft from curb cuts (ADA compliance)
7. **Check sidewalk width** - Minimum 3.25ft from tree bed to wall/fence
8. **Verify planting strip exists** - Space between curb and sidewalk

### Priority 3: MEDIUM
9. **Check utility clearances** - Gas, electric, water pipes
10. **Handle medians separately** - Different rules for median planting
11. **Distinguish street sides** - Don't double count if both sides have sidewalks

---

## 💡 **Why 2.2 Million is Unrealistic**

NYC currently has ~650,000 street trees. The code suggests we could plant **3.4x more trees** than currently exist, which is unrealistic because:

1. Most plantable locations already have trees
2. Many streets don't have sidewalks wide enough
3. Buildings, utilities, and infrastructure block many locations
4. Not all streets have sidewalks on both sides
5. Many locations are too close to intersections, lights, or other infrastructure

A more realistic estimate would be **100,000-300,000** additional plantable locations after applying all constraints.

---

## 📝 **Next Steps**

1. Load sidewalk data and filter to only sidewalk locations
2. Load building data and check clearances
3. Offset points from centerline to sidewalk (perpendicular offset)
4. Implement all missing constraint checks
5. Re-run generation with all constraints
6. Verify results are realistic
