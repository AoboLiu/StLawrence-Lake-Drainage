var ISLAND_ASSET =
  'projects/YOUR_PROJECT/assets/StLawrence_island';

var OUTPUT_ROOT =
  'projects/YOUR_PROJECT/assets/StLawrence_lakes_v2';

var START_YEAR = 1999;
var END_YEAR   = 2025;

var REF_START = 1999;
var REF_END   = 2016;

var WATER_PCT_THRESHOLD = 50;
var CORE_FREQ_THRESHOLD = 0.70;
var REF_EXTENT_FREQ_THRESHOLD = 0.50;
var MIN_VALID_REF_YEARS = 12;

var MIN_CORE_PIXELS = 2;
var MIN_REFERENCE_AREA_HA = 1.0;

var LOCAL_BUFFER_EQ_RADIUS_FACTOR = 2.0;
var MIN_LOCAL_BUFFER_M = 300;
var MAX_LOCAL_BUFFER_M = 1200;

var SCALE_M = 30;
var METRIC_CRS = 'EPSG:3995';

var SNIC_SIZE = 64;
var SNIC_COMPACTNESS = 1;
var SNIC_CONNECTIVITY = 8;
var SNIC_NEIGHBORHOOD = 512;

var BUILD_ANNUAL_TABLE = true;

var RUN_EXPORTS = false;

var islandFC = ee.FeatureCollection(ISLAND_ASSET);
var island = islandFC.geometry();

var GLAD_ANNUAL_ID = 'projects/glad/water/C2/annual';

Map.centerObject(islandFC, 8);

Map.addLayer(
  islandFC.style({
    color: '000000',
    fillColor: '00000000',
    width: 2
  }),
  {},
  'St. Lawrence Island LAND polygon',
  true
);

function annualPercent(year) {
  var raw = ee.Image(
    GLAD_ANNUAL_ID + '/' + String(year)
  ).select([0], ['water_pct']);

  var pct = raw
    .updateMask(raw.gte(0).and(raw.lte(100)))
    .toFloat()
    .clip(island);

  return pct.set({
    year: year,
    'system:time_start': ee.Date.fromYMD(year, 1, 1).millis()
  });
}

function annualWater(year) {
  var pct = annualPercent(year);

  return pct
    .gte(WATER_PCT_THRESHOLD)
    .rename('water')
    .toByte()
    .set({
      year: year,
      'system:time_start': ee.Date.fromYMD(year, 1, 1).millis()
    });
}

var allYears = [];
for (var y = START_YEAR; y <= END_YEAR; y++) {
  allYears.push(y);
}

var refYears = [];
for (var yr = REF_START; yr <= REF_END; yr++) {
  refYears.push(yr);
}

var annualPctCollection = ee.ImageCollection.fromImages(
  allYears.map(annualPercent)
);

var annualWaterCollection = ee.ImageCollection.fromImages(
  allYears.map(annualWater)
);

var refWaterCollection = ee.ImageCollection.fromImages(
  refYears.map(annualWater)
);

print('Annual GLAD years', annualPctCollection.aggregate_array('year'));
print('Reference years', refWaterCollection.aggregate_array('year'));

var refValidYears = refWaterCollection
  .count()
  .rename('valid_ref_years');

var refWaterYears = refWaterCollection
  .sum()
  .rename('water_ref_years');

var refWaterFrequency = refWaterYears
  .divide(refValidYears)
  .rename('ref_water_frequency')
  .updateMask(refValidYears.gt(0));

var rawCore = refWaterFrequency
  .gte(CORE_FREQ_THRESHOLD)
  .and(refValidYears.gte(MIN_VALID_REF_YEARS))
  .rename('core')
  .toByte()
  .selfMask()
  .reproject({
    crs: METRIC_CRS,
    scale: SCALE_M
  });

var pixelArea = ee.Image.pixelArea().rename('area_m2');

var coreSegmentsRaw = rawCore
  .rename('segment')
  .addBands(pixelArea)
  .reduceToVectors({
    reducer: ee.Reducer.sum().setOutputs(['core_area_m2']),
    geometry: island,
    scale: SCALE_M,
    geometryType: 'polygon',
    eightConnected: true,
    labelProperty: 'segment_value',
    crs: METRIC_CRS,
    maxPixels: 1e10,
    tileScale: 4,
    geometryInNativeProjection: true
  });

var minCoreAreaM2 = MIN_CORE_PIXELS * SCALE_M * SCALE_M;

var coreSegments = coreSegmentsRaw
  .filter(ee.Filter.gte('core_area_m2', minCoreAreaM2))
  .map(function(f) {
    f = ee.Feature(f);

    var c = f.geometry()
      .centroid(1)
      .transform('EPSG:4326', 1)
      .coordinates();

    var lon = ee.Number(c.get(0));
    var lat = ee.Number(c.get(1));

    var sortKey = lat.add(90)
      .multiply(1000)
      .add(lon.add(180));

    return f.set({
      centroid_lon: lon,
      centroid_lat: lat,
      spatial_sort_key: sortKey
    });
  })
  .sort('spatial_sort_key');

var coreCount = coreSegments.size();
var coreList = coreSegments.toList(coreCount);

var coreInventory = ee.FeatureCollection(
  ee.List.sequence(0, coreCount.subtract(1)).map(function(i) {
    i = ee.Number(i);

    var f = ee.Feature(coreList.get(i));
    var idNum = i.add(1);
    var idStr = ee.String('SLI_').cat(idNum.format('%05d'));

    return f.set({
      Lake_ID_num: idNum,
      Lake_ID: idStr,
      core_area_ha: ee.Number(f.get('core_area_m2')).divide(10000)
    });
  })
);

print('A01 persistent core count', coreInventory.size());
print('A02 first core feature', coreInventory.first());

var coreSeed = ee.Image.constant(0)
  .toByte()
  .paint(coreInventory, 1)
  .rename('seed')
  .selfMask()
  .clip(island)
  .reproject({
    crs: METRIC_CRS,
    scale: SCALE_M
  });

var referenceExtent = refWaterFrequency
  .gte(REF_EXTENT_FREQ_THRESHOLD)
  .and(refValidYears.gte(MIN_VALID_REF_YEARS))
  .rename('reference_extent')
  .toByte()
  .selfMask()
  .reproject({
    crs: METRIC_CRS,
    scale: SCALE_M
  });

var refSnicInput = ee.Image.constant(0)
  .rename('constant')
  .toFloat()
  .updateMask(referenceExtent)
  .reproject({
    crs: METRIC_CRS,
    scale: SCALE_M
  });

var refSnic = ee.Algorithms.Image.Segmentation.SNIC({
  image: refSnicInput,
  size: SNIC_SIZE,
  compactness: SNIC_COMPACTNESS,
  connectivity: SNIC_CONNECTIVITY,
  neighborhoodSize: SNIC_NEIGHBORHOOD,
  seeds: coreSeed
});

var refClusters = refSnic
  .select('clusters')
  .rename('ref_cluster')
  .updateMask(referenceExtent)
  .reproject({
    crs: METRIC_CRS,
    scale: SCALE_M
  });

var refLookup = refClusters.reduceRegions({
  collection: coreInventory,
  reducer: ee.Reducer.mode().setOutputs(['ref_cluster']),
  crs: METRIC_CRS,
  scale: SCALE_M,
  tileScale: 4
})
.filter(ee.Filter.notNull(['ref_cluster']));

print('A03 cores successfully linked to reference clusters',
      refLookup.size());

var refClusterIds = ee.List(refLookup.aggregate_array('ref_cluster'));
var refLakeIds    = ee.List(refLookup.aggregate_array('Lake_ID_num'));

var referenceOwnership = refClusters
  .remap(refClusterIds, refLakeIds)
  .rename('Lake_ID_num')
  .toInt32()
  .updateMask(referenceExtent);

var referenceObjects0 = referenceOwnership
  .addBands(pixelArea)
  .reduceToVectors({
    reducer: ee.Reducer.sum().setOutputs(['reference_area_m2']),
    geometry: island,
    scale: SCALE_M,
    geometryType: 'polygon',
    eightConnected: true,
    labelProperty: 'Lake_ID_num',
    crs: METRIC_CRS,
    maxPixels: 1e10,
    tileScale: 4,
    geometryInNativeProjection: true
  })
  .map(function(f) {
    f = ee.Feature(f);
    var idNum = ee.Number(f.get('Lake_ID_num'));

    return f.set({
      Lake_ID: ee.String('SLI_').cat(idNum.format('%05d')),
      reference_area_ha:
        ee.Number(f.get('reference_area_m2')).divide(10000)
    });
  });

var coreAreaImage = ee.Image.pixelArea()
  .updateMask(coreSeed)
  .rename('core_area_m2');

var referenceObjects = coreAreaImage.reduceRegions({
  collection: referenceObjects0,
  reducer: ee.Reducer.sum().setOutputs(['core_area_m2_check']),
  crs: METRIC_CRS,
  scale: SCALE_M,
  tileScale: 4
})
.map(function(f) {
  f = ee.Feature(f);

  var coreM2 = ee.Number(
    ee.Algorithms.If(
      ee.Algorithms.IsEqual(f.get('core_area_m2_check'), null),
      0,
      f.get('core_area_m2_check')
    )
  );

  return f.set({
    core_area_ha: coreM2.divide(10000)
  });
});

print('A04 reference object count', referenceObjects.size());
print('A05 first reference object', referenceObjects.first());

var referenceObjectsWithBuffer = referenceObjects.map(function(f) {
  f = ee.Feature(f);

  var areaM2 = ee.Number(f.get('reference_area_m2'));
  var eqRadiusM = areaM2.divide(Math.PI).sqrt();

  var localBufferM = eqRadiusM
    .multiply(LOCAL_BUFFER_EQ_RADIUS_FACTOR)
    .max(MIN_LOCAL_BUFFER_M)
    .min(MAX_LOCAL_BUFFER_M);

  return f
    .setGeometry(f.geometry().buffer(localBufferM, 1))
    .set({
      equivalent_radius_m: eqRadiusM,
      local_buffer_m: localBufferM
    });
});

var localNeighborhoodMask = ee.Image.constant(0)
  .toByte()
  .paint(referenceObjectsWithBuffer, 1)
  .rename('local_neighborhood')
  .selfMask()
  .clip(island)
  .reproject({
    crs: METRIC_CRS,
    scale: SCALE_M
  });

var candidateWaterAll = annualWaterCollection
  .max()
  .rename('candidate_water_all')
  .toByte()
  .selfMask()
  .reproject({
    crs: METRIC_CRS,
    scale: SCALE_M
  });

var candidateWaterLocal = candidateWaterAll
  .updateMask(localNeighborhoodMask)
  .rename('candidate_water_local')
  .selfMask();

var finalSnicInput = ee.Image.constant(0)
  .rename('constant')
  .toFloat()
  .updateMask(candidateWaterLocal)
  .reproject({
    crs: METRIC_CRS,
    scale: SCALE_M
  });

var finalSnic = ee.Algorithms.Image.Segmentation.SNIC({
  image: finalSnicInput,
  size: SNIC_SIZE,
  compactness: SNIC_COMPACTNESS,
  connectivity: SNIC_CONNECTIVITY,
  neighborhoodSize: SNIC_NEIGHBORHOOD,
  seeds: coreSeed
});

var finalClusters = finalSnic
  .select('clusters')
  .rename('final_cluster')
  .updateMask(candidateWaterLocal)
  .reproject({
    crs: METRIC_CRS,
    scale: SCALE_M
  });

var finalLookup = finalClusters.reduceRegions({
  collection: coreInventory,
  reducer: ee.Reducer.mode().setOutputs(['final_cluster']),
  crs: METRIC_CRS,
  scale: SCALE_M,
  tileScale: 4
})
.filter(ee.Filter.notNull(['final_cluster']));

print('A06 cores successfully linked to final clusters',
      finalLookup.size());

var finalClusterIds = ee.List(
  finalLookup.aggregate_array('final_cluster')
);

var finalLakeIds = ee.List(
  finalLookup.aggregate_array('Lake_ID_num')
);

var ownershipAllPreclip = finalClusters
  .remap(finalClusterIds, finalLakeIds)
  .rename('Lake_ID_num')
  .toInt32();

var ownershipZonesAll0 = ownershipAllPreclip
  .addBands(pixelArea)
  .reduceToVectors({
    reducer: ee.Reducer.sum().setOutputs(['preclip_area_m2']),
    geometry: island,
    scale: SCALE_M,
    geometryType: 'polygon',
    eightConnected: true,
    labelProperty: 'Lake_ID_num',
    crs: METRIC_CRS,
    maxPixels: 1e10,
    tileScale: 4,
    geometryInNativeProjection: true
  });

var localJoin = ee.Join.saveFirst('local_neighborhood_feature');
var localJoinCondition = ee.Filter.equals({
  leftField: 'Lake_ID_num',
  rightField: 'Lake_ID_num'
});

var ownershipJoined = ee.FeatureCollection(
  localJoin.apply(
    ownershipZonesAll0,
    referenceObjectsWithBuffer,
    localJoinCondition
  )
);

var ownershipZonesStrict = ownershipJoined.map(function(f) {
  f = ee.Feature(f);

  var localFeature = ee.Feature(
    f.get('local_neighborhood_feature')
  );

  var strictGeometry = f.geometry().intersection(
    localFeature.geometry(),
    1
  );

  return ee.Feature(strictGeometry).set({
    Lake_ID_num: f.get('Lake_ID_num')
  });
});

var ownershipAll = ee.Image.constant(0)
  .toInt32()
  .paint(ownershipZonesStrict, 'Lake_ID_num')
  .rename('Lake_ID_num')
  .selfMask()
  .clip(island)
  .reproject({
    crs: METRIC_CRS,
    scale: SCALE_M
  });

print('A06b strict per-lake ownership-zone count',
      ownershipZonesStrict.size());

var acceptedReferenceObjects = referenceObjects
  .filter(ee.Filter.gte(
    'reference_area_ha',
    MIN_REFERENCE_AREA_HA
  ))
  .sort('Lake_ID_num');

var acceptedLakeIds = ee.List(
  acceptedReferenceObjects.aggregate_array('Lake_ID_num')
);

var ownership = ownershipAll
  .remap(acceptedLakeIds, acceptedLakeIds)
  .rename('Lake_ID_num')
  .toInt32()
  .selfMask();

print('A07 reference lakes >=1 ha', acceptedReferenceObjects.size());

var lakeInventory0 = ownership
  .addBands(pixelArea)
  .reduceToVectors({
    reducer: ee.Reducer.sum().setOutputs(['ownership_area_m2']),
    geometry: island,
    scale: SCALE_M,
    geometryType: 'polygon',
    eightConnected: true,
    labelProperty: 'Lake_ID_num',
    crs: METRIC_CRS,
    maxPixels: 1e10,
    tileScale: 4,
    geometryInNativeProjection: true
  })
  .map(function(f) {
    f = ee.Feature(f);
    var idNum = ee.Number(f.get('Lake_ID_num'));

    return f.set({
      Lake_ID: ee.String('SLI_').cat(idNum.format('%05d')),
      ownership_area_ha:
        ee.Number(f.get('ownership_area_m2')).divide(10000)
    });
  });

var refAreaImage = ee.Image.pixelArea()
  .updateMask(referenceExtent)
  .rename('reference_area_m2');

var lakeInventory1 = refAreaImage.reduceRegions({
  collection: lakeInventory0,
  reducer: ee.Reducer.sum().setOutputs(['reference_area_m2_check']),
  crs: METRIC_CRS,
  scale: SCALE_M,
  tileScale: 4
});

var lakeInventory2 = coreAreaImage.reduceRegions({
  collection: lakeInventory1,
  reducer: ee.Reducer.sum().setOutputs(['core_area_m2_check2']),
  crs: METRIC_CRS,
  scale: SCALE_M,
  tileScale: 4
});

var lakeInventory = lakeInventory2.map(function(f) {
  f = ee.Feature(f);

  var refM2 = ee.Number(
    ee.Algorithms.If(
      ee.Algorithms.IsEqual(f.get('reference_area_m2_check'), null),
      0,
      f.get('reference_area_m2_check')
    )
  );

  var coreM2 = ee.Number(
    ee.Algorithms.If(
      ee.Algorithms.IsEqual(f.get('core_area_m2_check2'), null),
      0,
      f.get('core_area_m2_check2')
    )
  );

  var eqRadiusM = refM2.divide(Math.PI).sqrt();

  var localBufferM = eqRadiusM
    .multiply(LOCAL_BUFFER_EQ_RADIUS_FACTOR)
    .max(MIN_LOCAL_BUFFER_M)
    .min(MAX_LOCAL_BUFFER_M);

  return f.set({
    reference_area_ha: refM2.divide(10000),
    core_area_ha: coreM2.divide(10000),
    equivalent_radius_m: eqRadiusM,
    local_buffer_m: localBufferM
  });
})
.filter(ee.Filter.gte('reference_area_ha', MIN_REFERENCE_AREA_HA))
.sort('Lake_ID_num');

print('A08 FINAL lake inventory count', lakeInventory.size());
print('A09 first FINAL lake', lakeInventory.first());

function maskedAreaHa(maskImage, region) {
  var result = ee.Image.pixelArea()
    .updateMask(maskImage)
    .rename('area')
    .reduceRegion({
      reducer: ee.Reducer.sum(),
      geometry: region,
      crs: METRIC_CRS,
      scale: SCALE_M,
      maxPixels: 1e10,
      tileScale: 4
    });

  var m2 = ee.Number(
    ee.Algorithms.If(
      ee.Algorithms.IsEqual(result.get('area'), null),
      0,
      result.get('area')
    )
  );

  return m2.divide(10000);
}

var candidateOutsideLocal = candidateWaterAll
  .updateMask(localNeighborhoodMask.unmask(0).not());

var finalAssignedMask = ownershipAll.mask().unmask(0);

var localCandidateUnassigned = candidateWaterLocal
  .updateMask(finalAssignedMask.not());

print(
  'QA01 historical candidate water OUTSIDE local neighborhoods (ha)',
  maskedAreaHa(candidateOutsideLocal, island)
);

print(
  'QA02 LOCAL candidate water not assigned to any core (ha)',
  maskedAreaHa(localCandidateUnassigned, island)
);

print(
  'QA03 object counts',
  ee.Dictionary({
    core_count: coreInventory.size(),
    reference_object_count: referenceObjects.size(),
    accepted_reference_lakes_ge_1ha: acceptedReferenceObjects.size(),
    final_ownership_zone_count: lakeInventory.size()
  })
);

function valueOrZero(value) {
  return ee.Number(
    ee.Algorithms.If(
      ee.Algorithms.IsEqual(value, null),
      0,
      value
    )
  );
}

function annualLakeTable(year) {

  var pct = annualPercent(year);

  var area50 = ee.Image.pixelArea()
    .updateMask(pct.gte(WATER_PCT_THRESHOLD))
    .rename('area50_m2');

  var weightedArea = ee.Image.pixelArea()
    .multiply(pct.divide(100))
    .updateMask(pct.mask())
    .rename('weighted_area_m2');

  var validArea = ee.Image.pixelArea()
    .updateMask(pct.mask())
    .rename('valid_area_m2');

  var metricImage = area50
    .addBands(weightedArea)
    .addBands(validArea);

  var rows = metricImage.reduceRegions({
    collection: lakeInventory,
    reducer: ee.Reducer.sum(),
    crs: METRIC_CRS,
    scale: SCALE_M,
    tileScale: 4
  });

  return rows.map(function(f) {
    f = ee.Feature(f);

    var areaM2     = valueOrZero(f.get('area50_m2'));
    var weightedM2 = valueOrZero(f.get('weighted_area_m2'));
    var validM2    = valueOrZero(f.get('valid_area_m2'));

    var ownershipHa = ee.Number(f.get('ownership_area_ha'));
    var referenceHa = ee.Number(f.get('reference_area_ha'));

    var areaHa = areaM2.divide(10000);

    var validFraction = ee.Algorithms.If(
      ownershipHa.gt(0),
      validM2.divide(ownershipHa.multiply(10000)),
      null
    );

    var relativeArea = ee.Algorithms.If(
      referenceHa.gt(0),
      areaHa.divide(referenceHa),
      null
    );

    return ee.Feature(null, {
      Lake_ID_num: f.get('Lake_ID_num'),
      Lake_ID: f.get('Lake_ID'),
      year: year,

      area50_ha: areaHa,
      weighted_area_ha: weightedM2.divide(10000),
      valid_fraction: validFraction,
      relative_area: relativeArea,

      reference_area_ha: referenceHa,
      core_area_ha: f.get('core_area_ha'),
      ownership_area_ha: ownershipHa,

      equivalent_radius_m: f.get('equivalent_radius_m'),
      local_buffer_m: f.get('local_buffer_m')
    });
  });
}

var annualDynamics = ee.FeatureCollection([]);

if (BUILD_ANNUAL_TABLE) {
  annualDynamics = ee.FeatureCollection(
    allYears.map(function(year) {
      return annualLakeTable(year);
    })
  ).flatten();

  print('A10 annual lake-year row count', annualDynamics.size());
  print('A11 first annual record', annualDynamics.first());
}

Map.addLayer(
  refWaterFrequency,
  {
    min: 0,
    max: 1,
    palette: ['ffffff', '8ecae6', '023047']
  },
  '01 pre-event water frequency 1999–2016',
  false
);

Map.addLayer(
  coreSeed,
  {palette: ['00ffff']},
  '02 persistent lake cores',
  true
);

Map.addLayer(
  referenceOwnership.randomVisualizer(),
  {},
  '03 partitioned reference lake objects',
  false
);

Map.addLayer(
  localNeighborhoodMask,
  {palette: ['ffff00']},
  '04 allowed LOCAL ownership neighborhoods',
  false
);

Map.addLayer(
  candidateWaterAll,
  {palette: ['ff00ff']},
  '05 all historical candidate water 1999–2025',
  false
);

Map.addLayer(
  candidateWaterLocal,
  {palette: ['0066ff']},
  '06 LOCAL historical candidate water',
  false
);

Map.addLayer(
  ownership.randomVisualizer(),
  {},
  '07 FINAL LOCAL ownership zones / Lake_ID',
  true
);

Map.addLayer(
  lakeInventory.style({
    color: 'ffffff',
    fillColor: '00000000',
    width: 1
  }),
  {},
  '08 FINAL lake inventory outlines',
  false
);

Map.addLayer(
  candidateOutsideLocal,
  {palette: ['ff0000']},
  'QA candidate water outside local neighborhoods',
  false
);

Map.addLayer(
  localCandidateUnassigned,
  {palette: ['ff8800']},
  'QA local candidate water unassigned',
  false
);

if (RUN_EXPORTS) {

  Export.table.toAsset({
    collection: coreInventory,
    description: 'StLawrence_GLAD_reference_cores_v2',
    assetId: OUTPUT_ROOT + '_cores'
  });

  Export.table.toAsset({
    collection: acceptedReferenceObjects,
    description: 'StLawrence_GLAD_reference_objects_v2',
    assetId: OUTPUT_ROOT + '_reference_objects'
  });

  Export.table.toAsset({
    collection: lakeInventory,
    description: 'StLawrence_GLAD_local_ownership_inventory_v2',
    assetId: OUTPUT_ROOT + '_inventory'
  });

  Export.image.toAsset({
    image: ownership.toInt32(),
    description: 'StLawrence_GLAD_local_ownership_raster_v2',
    assetId: OUTPUT_ROOT + '_ownership',
    region: island,
    crs: METRIC_CRS,
    scale: SCALE_M,
    maxPixels: 1e10,
    pyramidingPolicy: {
      '.default': 'mode'
    }
  });

  if (BUILD_ANNUAL_TABLE) {
    Export.table.toDrive({
      collection: annualDynamics,
      description: 'StLawrence_GLAD_annual_dynamics_v2',
      fileNamePrefix: 'StLawrence_GLAD_annual_dynamics_v2',
      fileFormat: 'CSV'
    });
  }
}
