import math
import pandas as pd

def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance in kilometers between two WGS84 points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def detect_columns(df):
    """Auto-detect lat/lng/name columns from a DataFrame.
    
    Returns (lng_col, lat_col, name_col, merged_col) where:
    - If split columns found: lng_col and lat_col are set, merged_col is None
    - If merged column found: merged_col is set, lng_col and lat_col are None
    - name_col may be None if no name column detected
    """
    cols = {c.lower().strip(): c for c in df.columns}
    lng_candidates = ['lng', 'lon', 'longitude', '经度']
    lat_candidates = ['lat', 'latitude', '纬度']
    name_candidates = ['name', 'store_name', '门店名', '名称', '门店名称', 'id']
    merged_candidates = ['lnglat', 'lonlat', 'coordinates', '坐标', '经纬度']

    lng_col = next((cols[c] for c in lng_candidates if c in cols), None)
    lat_col = next((cols[c] for c in lat_candidates if c in cols), None)
    name_col = next((cols[c] for c in name_candidates if c in cols), None)

    # If both split columns found, use them
    if lng_col and lat_col:
        return lng_col, lat_col, name_col, None

    # Try named merged column candidates
    merged_col = next((cols[c] for c in merged_candidates if c in cols), None)

    # If no named merged column, scan all columns for "number,number" pattern
    if not merged_col:
        import re
        pattern = re.compile(r'^-?\d+\.?\d*,-?\d+\.?\d*$')
        for col in df.columns:
            sample = str(df[col].iloc[0]).strip()
            if pattern.match(sample):
                merged_col = col
                break

    return None, None, name_col, merged_col


def split_merged_coords(df, merged_col):
    """Split a 'lng,lat' merged column into two float Series."""
    split = df[merged_col].astype(str).str.split(',', expand=True)
    lng = split[0].astype(float)
    lat = split[1].astype(float)
    return lng, lat

def parse_radius_km(radius_str):
    """Parse radius string (e.g. '1km', '500m', '1.5公里') to float km."""
    s = str(radius_str).strip().lower()
    s = s.replace('公里', 'km').replace('千米', 'km').replace('米', 'm').replace(' ', '')
    if s.endswith('km'):
        return float(s[:-2])
    elif s.endswith('m'):
        return float(s[:-1]) / 1000
    else:
        return float(s)

def grade_competition(count, mean_val, std_val):
    """Assign competition intensity grade."""
    if count == 0:
        return '低'
    if count > mean_val + std_val:
        return '高'
    elif count < max(mean_val - std_val, 1):
        return '低'
    return '中'

def run_density_analysis(stores_df, competitors_df, radius_km):
    """
    Main analysis function.
    Returns a DataFrame with columns: 门店名称, 经度, 纬度, 竞争点数量, 均值偏差, 竞争强度等级
    Handles both split (lng col + lat col) and merged ('lng,lat' single col) coordinate formats.
    """
    s_lng, s_lat, s_name, s_merged = detect_columns(stores_df)
    c_lng, c_lat, _, c_merged = detect_columns(competitors_df)

    competitors_df = competitors_df.copy()
    if c_merged:
        competitors_df['_lon'], competitors_df['_lat'] = split_merged_coords(competitors_df, c_merged)
    else:
        competitors_df['_lat'] = competitors_df[c_lat].astype(float)
        competitors_df['_lon'] = competitors_df[c_lng].astype(float)

    results = []
    for idx, row in stores_df.iterrows():
        name = row[s_name] if s_name else f"门店{idx+1}"
        if s_merged:
            parts = str(row[s_merged]).split(',')
            lon, lat = float(parts[0]), float(parts[1])
        else:
            lat = float(row[s_lat])
            lon = float(row[s_lng])
        count = sum(
            1 for _, cr in competitors_df.iterrows()
            if haversine_km(lat, lon, cr['_lat'], cr['_lon']) <= radius_km
        )
        results.append({'门店名称': name, '经度': lon, '纬度': lat, '竞争点数量': count})

    df = pd.DataFrame(results)
    mean_val = df['竞争点数量'].mean()
    std_val = df['竞争点数量'].std(ddof=0)

    df['均值偏差'] = (df['竞争点数量'] - mean_val).round(2)
    df['竞争强度等级'] = df['竞争点数量'].apply(lambda x: grade_competition(x, mean_val, std_val))

    return df, mean_val, std_val


def generate_competition_grid(competitors_df, radius_km):
    """
    Generate a grid covering all competitor points.
    Cell size = radius_km (same scale as the buffer analysis).

    Returns a DataFrame with columns: wkt, count
    - wkt: WKT POLYGON string for each cell
    - count: number of competitor points falling inside the cell
    """
    c_lng, c_lat, _, c_merged = detect_columns(competitors_df)

    if c_merged:
        lngs, lats = split_merged_coords(competitors_df, c_merged)
    else:
        lngs = competitors_df[c_lng].astype(float)
        lats = competitors_df[c_lat].astype(float)

    min_lng, max_lng = lngs.min(), lngs.max()
    min_lat, max_lat = lats.min(), lats.max()
    center_lat = (min_lat + max_lat) / 2.0

    # Cell size in degrees
    cell_lat = radius_km / 111.0
    cell_lng = radius_km / (111.0 * math.cos(math.radians(center_lat)))

    # Expand bbox by half a cell on each side
    grid_min_lng = min_lng - cell_lng * 0.5
    grid_min_lat = min_lat - cell_lat * 0.5
    grid_max_lng = max_lng + cell_lng * 0.5
    grid_max_lat = max_lat + cell_lat * 0.5

    # Grid dimensions
    n_cols = max(1, math.ceil((grid_max_lng - grid_min_lng) / cell_lng))
    n_rows = max(1, math.ceil((grid_max_lat - grid_min_lat) / cell_lat))
    total_cells = n_cols * n_rows

    if total_cells > 10000:
        # Scale up cell size to keep grid manageable
        scale = math.sqrt(total_cells / 10000.0)
        cell_lat *= scale
        cell_lng *= scale
        n_cols = max(1, math.ceil((grid_max_lng - grid_min_lng) / cell_lng))
        n_rows = max(1, math.ceil((grid_max_lat - grid_min_lat) / cell_lat))

    # Precompute competitor point arrays for fast lookup
    comp_lngs = lngs.values
    comp_lats = lats.values

    rows = []
    for row in range(n_rows):
        lat0 = grid_min_lat + row * cell_lat
        lat1 = lat0 + cell_lat
        for col in range(n_cols):
            lng0 = grid_min_lng + col * cell_lng
            lng1 = lng0 + cell_lng

            # Count points inside cell (simple bbox test)
            count = int(((comp_lngs >= lng0) & (comp_lngs < lng1) &
                         (comp_lats >= lat0) & (comp_lats < lat1)).sum())

            # WKT: bottom-left → bottom-right → top-right → top-left → close
            wkt = (f"POLYGON(({lng0:.6f} {lat0:.6f}, "
                   f"{lng1:.6f} {lat0:.6f}, "
                   f"{lng1:.6f} {lat1:.6f}, "
                   f"{lng0:.6f} {lat1:.6f}, "
                   f"{lng0:.6f} {lat0:.6f}))")
            rows.append({"wkt": wkt, "count": count})

    return pd.DataFrame(rows), n_cols, n_rows, cell_lng, cell_lat
