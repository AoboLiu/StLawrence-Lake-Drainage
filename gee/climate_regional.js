var ISLAND_ASSET = 'projects/YOUR_PROJECT/assets/StLawrence_island';
var island = ee.FeatureCollection(ISLAND_ASSET).geometry();
var climate = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR')
  .filterDate('2016-04-01', '2024-09-18');

function exposure(end, days) {
  var c = climate.filterDate(end.advance(-days, 'day'), end);
  var prefix = 'pre' + days + '_';
  var image = ee.Image.cat([
    c.select('temperature_2m').mean().subtract(273.15).rename(prefix + 't2m_mean_c'),
    c.select('total_precipitation_sum').sum().multiply(1000).rename(prefix + 'prcp_sum_mm'),
    c.select('snowmelt_sum').sum().multiply(1000).rename(prefix + 'snowmelt_sum_mm'),
    c.select('runoff_sum').sum().multiply(1000).rename(prefix + 'runoff_sum_mm')
  ]);
  return image.reduceRegion({
    reducer: ee.Reducer.mean(), geometry: island, scale: 11132,
    maxPixels: 1e8, tileScale: 4
  });
}

var years = ee.List.sequence(2016, 2024);
var rows = ee.FeatureCollection(years.map(function(year) {
  return ee.FeatureCollection(ee.List.sequence(0, 19).map(function(index) {
    var start = ee.Date.fromYMD(year, 5, 1).advance(ee.Number(index).multiply(7), 'day');
    return ee.Feature(null, {
      year: year, week_of_season: ee.Number(index).add(1),
      week_start: start.format('YYYY-MM-dd'),
      week_end: start.advance(6, 'day').format('YYYY-MM-dd')
    }).set(exposure(start, 7)).set(exposure(start, 14)).set(exposure(start, 30));
  }));
})).flatten();

Export.table.toDrive({
  collection: rows, description: 'SLI_regional_climate_reconstructed',
  fileNamePrefix: 'SLI_regional_climate_reconstructed', fileFormat: 'CSV'
});
