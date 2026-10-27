var ISLAND_ASSET =
  'projects/YOUR_PROJECT/assets/StLawrence_island';

var OWNERSHIP_ASSET =
  'projects/YOUR_PROJECT/assets/StLawrence_v4_ownership';

var INVENTORY_ASSET =
  'projects/YOUR_PROJECT/assets/StLawrence_v4_2_inventory';

var HLS_EVENT_ASSET =
  'projects/YOUR_PROJECT/assets/SLI_S1_manifest_v3_1_ALL_primary_openwater';

var EVENT_YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024];

var PAD_BEFORE_DAYS = 18;
var PAD_AFTER_DAYS  = 18;

var S1_ID = 'COPERNICUS/S1_GRD';
var INSTRUMENT_MODE = 'IW';
var RESOLUTION_METERS = 10;

var USE_ANGLE_MASK = true;
var MIN_ANGLE_DEG = 30;
var MAX_ANGLE_DEG = 46;

var MIN_VALID_FRACTION = 0.60;
var S1_SCALE_M = 10;
var METRIC_CRS = 'EPSG:3995';

var islandFC = ee.FeatureCollection(ISLAND_ASSET);
var island = islandFC.geometry();

var ownership = ee.Image(OWNERSHIP_ASSET)
  .select('Lake_ID_num')
  .toInt32();

var inventory = ee.FeatureCollection(INVENTORY_ASSET);
var allEvents = ee.FeatureCollection(HLS_EVENT_ASSET);

print('Final same-season HLS events', allEvents.size());

function prepS1(image) {
  image = ee.Image(image);

  var vv = image.select('VV').rename('vv_db');
  var vh = image.select('VH').rename('vh_db');
  var angle = image.select('angle').rename('angle_deg');

  var valid = vv.mask().and(vh.mask());

  if (USE_ANGLE_MASK) {
    valid = valid
      .and(angle.gte(MIN_ANGLE_DEG))
      .and(angle.lte(MAX_ANGLE_DEG));
  }

  vv = vv.updateMask(valid);
  vh = vh.updateMask(valid);
  angle = angle.updateMask(valid);

  var vvMinusVh = vv.subtract(vh)
    .rename('vv_minus_vh_db');

  var vvLinear = ee.Image(10)
    .pow(vv.divide(10))
    .rename('vv_linear');

  var vhLinear = ee.Image(10)
    .pow(vh.divide(10))
    .rename('vh_linear');

  var validBand = ee.Image.constant(1)
    .rename('valid')
    .updateMask(valid);

  var dateStr =
    ee.Date(image.get('system:time_start')).format('YYYY-MM-dd');

  var pass = ee.String(image.get('orbitProperties_pass'));
  var relOrbit = ee.Number(image.get('relativeOrbitNumber_start'));

  var key = dateStr
    .cat('_')
    .cat(pass)
    .cat('_R')
    .cat(relOrbit.format('%03d'));

  return vv
    .addBands(vh)
    .addBands(vvMinusVh)
    .addBands(vvLinear)
    .addBands(vhLinear)
    .addBands(angle)
    .addBands(validBand)
    .copyProperties(image, image.propertyNames())
    .set({
      date_str: dateStr,
      pass: pass,
      relative_orbit: relOrbit,
      acquisition_key: key
    });
}

function trackDailyMosaics(collection) {
  var keys = ee.List(
    collection.aggregate_array('acquisition_key')
  ).distinct().sort();

  return ee.ImageCollection.fromImages(
    keys.map(function(key) {
      key = ee.String(key);

      var subset = collection.filter(
        ee.Filter.eq('acquisition_key', key)
      );

      var first = ee.Image(subset.first());

      return subset.mosaic().set({
        acquisition_key: key,
        date_str: first.get('date_str'),
        pass: first.get('pass'),
        relative_orbit: first.get('relative_orbit'),
        platform_number: first.get('platform_number'),
        n_scenes: subset.size(),
        'system:time_start': ee.Date(first.get('date_str')).millis()
      });
    })
  );
}

function buildYearTable(targetYear) {
  targetYear = Number(targetYear);

  var eventsRaw = allEvents
    .filter(ee.Filter.eq('event_year', targetYear));

  var events = eventsRaw.map(function(f) {
    f = ee.Feature(f);

    var lastPre = ee.Date(f.get('LastPre'));
    var firstPost = ee.Date(f.get('FirstPost'));

    return f.set({
      lastpre_ms: lastPre.millis(),
      firstpost_ms: firstPost.millis(),
      event_window_start_ms:
        lastPre.advance(-PAD_BEFORE_DAYS, 'day').millis(),
      event_window_end_ms:
        firstPost.advance(PAD_AFTER_DAYS, 'day').millis()
    });
  });

  var targetIds = ee.List(
    events.aggregate_array('Lake_ID_num')
  ).distinct();

  var targetInventory = inventory.filter(
    ee.Filter.inList('Lake_ID_num', targetIds)
  );

  var targetMask = ownership.remap({
    from: targetIds,
    to: ee.List.repeat(1, targetIds.size()),
    defaultValue: 0
  }).rename('target').selfMask();

  var targetZones = ownership.updateMask(targetMask);

  var globalStart = ee.Date(
    ee.Number(events.aggregate_min('event_window_start_ms'))
  );

  var globalEnd = ee.Date(
    ee.Number(events.aggregate_max('event_window_end_ms'))
  ).advance(1, 'day');

  var s1Raw = ee.ImageCollection(S1_ID)
    .filterBounds(island)
    .filterDate(globalStart, globalEnd)
    .filter(ee.Filter.listContains(
      'transmitterReceiverPolarisation', 'VV'))
    .filter(ee.Filter.listContains(
      'transmitterReceiverPolarisation', 'VH'))
    .filter(ee.Filter.eq('instrumentMode', INSTRUMENT_MODE))
    .filter(ee.Filter.eq('resolution_meters', RESOLUTION_METERS))
    .map(prepS1);

  var s1Daily = trackDailyMosaics(s1Raw);

  function sceneLakeMetrics(image) {
    image = ee.Image(image);
    var zoneMask = targetZones.mask();

    var medianImage = image
      .select(['vv_db', 'vh_db', 'vv_minus_vh_db', 'angle_deg'])
      .updateMask(zoneMask)
      .addBands(targetZones);

    var medDict = ee.Dictionary(
      medianImage.reduceRegion({
        reducer: ee.Reducer.median()
          .repeat(4)
          .group({
            groupField: 4,
            groupName: 'Lake_ID_num'
          }),
        geometry: island,
        crs: METRIC_CRS,
        scale: S1_SCALE_M,
        maxPixels: 1e10,
        tileScale: 4
      })
    );

    var medGroups = ee.List(
      ee.Algorithms.If(
        medDict.contains('groups'),
        medDict.get('groups'),
        ee.List([])
      )
    );

    var medTable = ee.FeatureCollection(
      medGroups.map(function(d) {
        d = ee.Dictionary(d);
        var vals = ee.List(d.get('median'));

        return ee.Feature(null, {
          Lake_ID_num: d.get('Lake_ID_num'),
          vv_db_median: vals.get(0),
          vh_db_median: vals.get(1),
          vv_minus_vh_db_median: vals.get(2),
          angle_median: vals.get(3)
        });
      })
    );

    var linearImage = image
      .select(['vv_linear', 'vh_linear'])
      .updateMask(zoneMask)
      .addBands(targetZones);

    var meanDict = ee.Dictionary(
      linearImage.reduceRegion({
        reducer: ee.Reducer.mean()
          .repeat(2)
          .group({
            groupField: 2,
            groupName: 'Lake_ID_num'
          }),
        geometry: island,
        crs: METRIC_CRS,
        scale: S1_SCALE_M,
        maxPixels: 1e10,
        tileScale: 4
      })
    );

    var meanGroups = ee.List(
      ee.Algorithms.If(
        meanDict.contains('groups'),
        meanDict.get('groups'),
        ee.List([])
      )
    );

    var meanTable = ee.FeatureCollection(
      meanGroups.map(function(d) {
        d = ee.Dictionary(d);
        var vals = ee.List(d.get('mean'));

        return ee.Feature(null, {
          Lake_ID_num: d.get('Lake_ID_num'),
          vv_linear_mean: vals.get(0),
          vh_linear_mean: vals.get(1)
        });
      })
    );

    var validArea = ee.Image.pixelArea()
      .updateMask(image.select('valid').mask())
      .rename('valid_area_m2')
      .updateMask(zoneMask)
      .addBands(targetZones);

    var validDict = ee.Dictionary(
      validArea.reduceRegion({
        reducer: ee.Reducer.sum()
          .group({
            groupField: 1,
            groupName: 'Lake_ID_num'
          }),
        geometry: island,
        crs: METRIC_CRS,
        scale: S1_SCALE_M,
        maxPixels: 1e10,
        tileScale: 4
      })
    );

    var validGroups = ee.List(
      ee.Algorithms.If(
        validDict.contains('groups'),
        validDict.get('groups'),
        ee.List([])
      )
    );

    var validTable = ee.FeatureCollection(
      validGroups.map(function(d) {
        d = ee.Dictionary(d);
        return ee.Feature(null, {
          Lake_ID_num: d.get('Lake_ID_num'),
          valid_area_m2: d.get('sum')
        });
      })
    );

    var medMean = ee.FeatureCollection(
      ee.Join.saveFirst('mean_match').apply({
        primary: medTable,
        secondary: meanTable,
        condition: ee.Filter.equals({
          leftField: 'Lake_ID_num',
          rightField: 'Lake_ID_num'
        })
      })
    );

    var metrics = ee.FeatureCollection(
      ee.Join.saveFirst('valid_match').apply({
        primary: medMean,
        secondary: validTable,
        condition: ee.Filter.equals({
          leftField: 'Lake_ID_num',
          rightField: 'Lake_ID_num'
        })
      })
    );

    var withInv = ee.FeatureCollection(
      ee.Join.saveFirst('inv_match').apply({
        primary: metrics,
        secondary: targetInventory,
        condition: ee.Filter.equals({
          leftField: 'Lake_ID_num',
          rightField: 'Lake_ID_num'
        })
      })
    );

    var withEvent = ee.FeatureCollection(
      ee.Join.saveFirst('event_match').apply({
        primary: withInv,
        secondary: events,
        condition: ee.Filter.equals({
          leftField: 'Lake_ID_num',
          rightField: 'Lake_ID_num'
        })
      })
    );

    var sceneMs = ee.Date(image.get('date_str')).millis();

    return withEvent
      .filter(ee.Filter.notNull([
        'mean_match', 'valid_match', 'inv_match', 'event_match'
      ]))
      .map(function(f) {
        f = ee.Feature(f);

        var meanF = ee.Feature(f.get('mean_match'));
        var validF = ee.Feature(f.get('valid_match'));
        var invF = ee.Feature(f.get('inv_match'));
        var eventF = ee.Feature(f.get('event_match'));

        var validM2 = ee.Number(validF.get('valid_area_m2'));
        var ownershipM2 = ee.Number(invF.get('ownership_area_ha'))
          .multiply(10000);

        var lastPreMs = ee.Number(eventF.get('lastpre_ms'));
        var firstPostMs = ee.Number(eventF.get('firstpost_ms'));
        var windowStartMs = ee.Number(eventF.get('event_window_start_ms'));
        var windowEndMs = ee.Number(eventF.get('event_window_end_ms'));

        var inWindow = sceneMs.gte(windowStartMs)
          .and(sceneMs.lte(windowEndMs));

        var position = ee.String(
          ee.Algorithms.If(
            sceneMs.lte(lastPreMs),
            'PRE_CONTEXT',
            ee.Algorithms.If(
              sceneMs.gte(firstPostMs),
              'POST_CONTEXT',
              'INSIDE_HLS_BRACKET'
            )
          )
        );

        return ee.Feature(null, {
          Event_ID: eventF.get('Event_ID'),
          Lake_ID_num: f.get('Lake_ID_num'),
          Lake_ID: invF.get('Lake_ID'),
          event_year: targetYear,
          direction: eventF.get('direction'),
          state_transition_class: eventF.get('state_transition_class'),
          timing_type: eventF.get('timing_type'),
          HLS_confidence: eventF.get('HLS_confidence'),

          HLS_LastPre: eventF.get('LastPre'),
          HLS_FirstPost: eventF.get('FirstPost'),
          HLS_window_days: eventF.get('HLS_window_days'),

          s1_date: image.get('date_str'),
          s1_time_ms: sceneMs,
          s1_position: position,

          platform_number: image.get('platform_number'),
          orbit_pass: image.get('pass'),
          relative_orbit: image.get('relative_orbit'),
          acquisition_key: image.get('acquisition_key'),
          n_scenes: image.get('n_scenes'),

          valid_area_ha: validM2.divide(10000),
          valid_fraction: validM2.divide(ownershipM2),

          vv_db_median: f.get('vv_db_median'),
          vh_db_median: f.get('vh_db_median'),
          vv_minus_vh_db_median: f.get('vv_minus_vh_db_median'),
          vv_linear_mean: meanF.get('vv_linear_mean'),
          vh_linear_mean: meanF.get('vh_linear_mean'),
          angle_median: f.get('angle_median'),
          in_event_window: inWindow
        });
      })
      .filter(ee.Filter.eq('in_event_window', 1))
      .filter(ee.Filter.gte('valid_fraction', MIN_VALID_FRACTION));
  }

  function collectionToTable(collection) {
    var n = collection.size();
    var list = collection.toList(n);

    var tables = ee.List.sequence(0, n.subtract(1)).map(function(i) {
      return sceneLakeMetrics(ee.Image(list.get(i)));
    });

    return ee.FeatureCollection(tables).flatten();
  }

  return collectionToTable(s1Daily);
}

var allS1Table = ee.FeatureCollection([]);

EVENT_YEARS.forEach(function(y) {
  allS1Table = allS1Table.merge(buildYearTable(y));
});

Export.table.toDrive({
  collection: allS1Table,
  description: 'SLI_S1_V3_1_ALL_PRIMARY_OPENWATER',
  fileNamePrefix: 'SLI_S1_V3_1_ALL_PRIMARY_OPENWATER',
  fileFormat: 'CSV'
});

Map.centerObject(islandFC, 8);

print(
  'One export task created for all v3.1 primary-open-water same-season persistent events. ' +
  'Do NOT call allS1Table.size() in Console; start the Batch task directly.'
);
