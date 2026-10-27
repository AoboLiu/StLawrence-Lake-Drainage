var REFERENCE_ASSET = 'projects/YOUR_PROJECT/assets/StLawrence_lakes_v2_reference_objects';
var ISLAND_ASSET = 'projects/YOUR_PROJECT/assets/StLawrence_island';
var SCALE = 10;
var CRS = 'EPSG:3995';
var lakes = ee.FeatureCollection(REFERENCE_ASSET);
var island = ee.FeatureCollection(ISLAND_ASSET).geometry();
var water = ee.Image.constant(0).byte().paint(lakes, 1);
var dem = ee.Image('UMN/PGC/ArcticDEM/V4/2m_mosaic').select('elevation')
  .clip(island).updateMask(water.eq(0));

function percentiles(geom) {
  return dem.reduceRegion({
    reducer: ee.Reducer.percentile([10, 25, 50, 90]),
    geometry: geom, scale: SCALE, crs: CRS, maxPixels: 1e8, tileScale: 4
  });
}

function measure(feature) {
  feature = ee.Feature(feature);
  var lake = feature.geometry();
  var ring = lake.buffer(60, 1).difference(lake.buffer(30, 1), 1);
  var p = ee.Dictionary(percentiles(ring));
  var result = ee.Feature(null, {
    Lake_ID: feature.get('Lake_ID'),
    Lake_ID_num: feature.get('Lake_ID_num'),
    dem_scale_m: SCALE
  });
  var valid = p.contains('elevation_p50');
  var level = ee.Number(p.get('elevation_p50', 0));
  var near = ee.Dictionary({
    near30_60_elev_median_m: level,
    near30_60_elev_p10_m: p.get('elevation_p10', 0),
    near30_60_elev_p90_m: p.get('elevation_p90', 0),
    near30_60_bank_relief_p90_p10_m: ee.Number(p.get('elevation_p90', 0))
      .subtract(ee.Number(p.get('elevation_p10', 0)))
  });
  result = result.set(ee.Dictionary(ee.Algorithms.If(valid, near, ee.Dictionary({}))));
  [150, 300, 600, 1000].forEach(function(radius) {
    var area = lake.buffer(radius, 1).difference(lake, 1);
    var q = ee.Dictionary(percentiles(area));
    var values = ee.Dictionary({});
    [10, 25].forEach(function(pct) {
      var key = 'elevation_p' + pct;
      var pairs = ee.Dictionary().set('r' + radius + '_elev_p' + pct + '_m', q.get(key, 0))
        .set('r' + radius + '_drop_to_p' + pct + '_m', level.subtract(ee.Number(q.get(key, 0))));
      values = values.combine(ee.Dictionary(ee.Algorithms.If(valid.and(q.contains(key)), pairs, ee.Dictionary({}))));
    });
    [0.5, 1.0].forEach(function(drop) {
      var suffix = drop === 0.5 ? '0p5m' : '1m';
      var value = dem.lte(level.subtract(drop)).rename('fraction').reduceRegion({
        reducer: ee.Reducer.mean(), geometry: area, scale: SCALE, crs: CRS,
        maxPixels: 1e8, tileScale: 4
      }).get('fraction');
      values = values.set('r' + radius + '_frac_below_level_minus' + suffix,
        ee.Algorithms.If(valid, value, null));
    });
    result = result.set(values);
  });
  return result;
}

Export.table.toDrive({
  collection: lakes.map(measure), description: 'SLI_terrain_reconstructed',
  fileNamePrefix: 'SLI_terrain_reconstructed', fileFormat: 'CSV'
});
