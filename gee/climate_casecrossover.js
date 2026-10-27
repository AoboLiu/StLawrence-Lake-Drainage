var MANIFEST =
  'projects/YOUR_PROJECT/assets/SLI_casecrossover_FINAL_v3_1';

var DAYMET='NASA/ORNL/DAYMET_V4';
var ERA5='ECMWF/ERA5_LAND/DAILY_AGGR';

var rows=ee.FeatureCollection(MANIFEST);

function pt(f) {
  f=ee.Feature(f);
  return ee.Geometry.Point([
    ee.Number(f.get('longitude')),
    ee.Number(f.get('latitude'))
  ]);
}

function prepD(img) {
  img=ee.Image(img);
  var tx=img.select('tmax').rename('tmax_c');
  var tn=img.select('tmin').rename('tmin_c');
  var tm=tx.add(tn).divide(2).rename('tmean_c');
  var pdd=tm.max(0).rename('PDD');
  var ft=tn.lt(0).and(tx.gt(0)).rename('freeze_thaw_day').toFloat();
  return img.select(['prcp','swe'])
    .addBands([tx,tn,tm,pdd,ft])
    .copyProperties(img,['system:time_start']);
}

function dDict(p,s,e,prefix) {
  var c=ee.ImageCollection(DAYMET).filterDate(s,e).map(prepD);
  var first=ee.Image(c.sort('system:time_start').first());
  var last=ee.Image(c.sort('system:time_start',false).first());

  var x=ee.Image.cat([
    c.select('prcp').sum().rename(prefix+'_prcp_sum_mm'),
    c.select('prcp').max().rename(prefix+'_prcp_max1d_mm'),
    c.select('tmean_c').mean().rename(prefix+'_tmean_mean_c'),
    c.select('tmax_c').max().rename(prefix+'_tmax_max_c'),
    c.select('PDD').sum().rename(prefix+'_PDD_cday'),
    c.select('freeze_thaw_day').sum().rename(prefix+'_freeze_thaw_days'),
    first.select('swe').subtract(last.select('swe')).rename(prefix+'_swe_loss_mm')
  ]).toFloat();

  return ee.Dictionary(x.reduceRegion({
    reducer:ee.Reducer.mean(),
    geometry:p.buffer(1000),
    scale:1000,
    maxPixels:1e6
  }));
}

function prepE(img) {
  img=ee.Image(img);
  return ee.Image.cat([
    img.select('temperature_2m').subtract(273.15).rename('t2m_c'),
    img.select('total_precipitation_sum').multiply(1000).rename('prcp_mm'),
    img.select('snowmelt_sum').multiply(1000).rename('snowmelt_mm'),
    img.select('runoff_sum').multiply(1000).rename('runoff_mm'),
    img.select('volumetric_soil_water_layer_1').rename('soil_water_l1')
  ]).copyProperties(img,['system:time_start']);
}

function eDict(p,s,e,prefix) {
  var c=ee.ImageCollection(ERA5).filterDate(s,e).map(prepE);

  var x=ee.Image.cat([
    c.select('t2m_c').mean().rename(prefix+'_t2m_mean_c'),
    c.select('t2m_c').max().rename(prefix+'_t2m_max_c'),
    c.select('prcp_mm').sum().rename(prefix+'_prcp_sum_mm'),
    c.select('prcp_mm').max().rename(prefix+'_prcp_max1d_mm'),
    c.select('snowmelt_mm').sum().rename(prefix+'_snowmelt_sum_mm'),
    c.select('snowmelt_mm').max().rename(prefix+'_snowmelt_max1d_mm'),
    c.select('runoff_mm').sum().rename(prefix+'_runoff_sum_mm'),
    c.select('soil_water_l1').mean().rename(prefix+'_soil_water_mean')
  ]).toFloat();

  return ee.Dictionary(x.reduceRegion({
    reducer:ee.Reducer.mean(),
    geometry:p.buffer(6000),
    scale:11132,
    maxPixels:1e6
  }));
}

function addD(f) {
  f=ee.Feature(f);
  var p=pt(f);
  var s=ee.Date(f.get('index_start'));
  var e=ee.Date(f.get('index_end'));

  return f
    .set(dDict(p,s.advance(-7,'day'),s,'pre7'))
    .set(dDict(p,s.advance(-14,'day'),s,'pre14'))
    .set(dDict(p,s.advance(-30,'day'),s,'pre30'))
    .set(dDict(p,s.advance(1,'day'),e.advance(1,'day'),'bracket'))
    .setGeometry(null);
}

function addE(f) {
  f=ee.Feature(f);
  var p=pt(f);
  var s=ee.Date(f.get('index_start'));
  var e=ee.Date(f.get('index_end'));

  return f
    .set(eDict(p,s.advance(-7,'day'),s,'pre7'))
    .set(eDict(p,s.advance(-14,'day'),s,'pre14'))
    .set(eDict(p,s.advance(-30,'day'),s,'pre30'))
    .set(eDict(p,s.advance(1,'day'),e.advance(1,'day'),'bracket'))
    .setGeometry(null);
}

Export.table.toDrive({
  collection:rows.map(addD),
  description:'SLI_casecrossover_FINAL_v3_1_DAYMET',
  fileNamePrefix:'SLI_casecrossover_FINAL_v3_1_DAYMET',
  fileFormat:'CSV'
});

Export.table.toDrive({
  collection:rows.map(addE),
  description:'SLI_casecrossover_FINAL_v3_1_ERA5LAND',
  fileNamePrefix:'SLI_casecrossover_FINAL_v3_1_ERA5LAND',
  fileFormat:'CSV'
});
