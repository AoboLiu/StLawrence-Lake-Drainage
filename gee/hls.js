var ISLAND_ASSET =
  'projects/YOUR_PROJECT/assets/StLawrence_island';

var OWNERSHIP_ASSET =
  'projects/YOUR_PROJECT/assets/StLawrence_v4_ownership';

var INVENTORY_ASSET =
  'projects/YOUR_PROJECT/assets/StLawrence_v4_2_inventory';

var CANDIDATE_ASSET =
  'projects/YOUR_PROJECT/assets/SLI_GLAD_candidate_runs_v3';

var YEARS =
  [2014,2015,2016,2017,2018,2019,
   2020,2021,2022,2023,2024,2025];

var START_MONTH = 3;
var END_MONTH = 10;

var MASK_ADJACENT_TO_CLOUD = false;
var MASK_HIGH_AEROSOL = false;

var MIN_VALID_FRACTION = 0.60;

var SCALE_M = 30;
var METRIC_CRS = 'EPSG:3995';

var HLS_L30 = 'NASA/HLS/HLSL30/v002';
var HLS_S30 = 'NASA/HLS/HLSS30/v002';

var islandFC = ee.FeatureCollection(ISLAND_ASSET);
var island = islandFC.geometry();

var ownership =
  ee.Image(OWNERSHIP_ASSET)
    .select('Lake_ID_num')
    .toInt32();

var inventory =
  ee.FeatureCollection(INVENTORY_ASSET);

var candidates =
  ee.FeatureCollection(CANDIDATE_ASSET);

function qaMask(image) {
  var f = image.select('Fmask');

  var cloud = f.bitwiseAnd(1 << 1).eq(0);
  var adjacent = f.bitwiseAnd(1 << 2).eq(0);
  var shadow = f.bitwiseAnd(1 << 3).eq(0);
  var snowIce = f.bitwiseAnd(1 << 4).eq(0);

  var mask = cloud.and(shadow).and(snowIce);

  if (MASK_ADJACENT_TO_CLOUD) {
    mask = mask.and(adjacent);
  }

  if (MASK_HIGH_AEROSOL) {
    var aerosol = f.rightShift(6).bitwiseAnd(3);
    mask = mask.and(aerosol.neq(3));
  }

  return mask;
}

function addMetrics(common, fmask) {
  var green = common.select('green');
  var nir = common.select('nir');
  var swir1 = common.select('swir1');
  var swir2 = common.select('swir2');

  var awei = green.subtract(swir1)
    .multiply(4)
    .subtract(
      nir.multiply(0.25)
        .add(swir2.multiply(2.75))
    )
    .rename('awei');

  var mndwi = green.subtract(swir1)
    .divide(green.add(swir1))
    .rename('mndwi');

  var aweiWater =
    awei.gt(0).rename('awei_water');

  var mndwiWater =
    mndwi.gt(0).rename('mndwi_water');

  var fmaskWater = fmask
    .bitwiseAnd(1 << 5)
    .neq(0)
    .rename('fmask_water')
    .updateMask(common.select('green').mask());

  var valid = ee.Image.constant(1)
    .rename('valid')
    .updateMask(common.select('green').mask());

  return common
    .addBands(awei)
    .addBands(mndwi)
    .addBands(aweiWater)
    .addBands(mndwiWater)
    .addBands(fmaskWater)
    .addBands(valid);
}

function prepL30(image) {
  image = ee.Image(image);

  var green = image.select('B3').rename('green');
  var nir = image.select('B5').rename('nir');
  var swir1 = image.select('B6').rename('swir1');
  var swir2 = image.select('B7').rename('swir2');

  var valid = qaMask(image)
    .and(green.mask())
    .and(nir.mask())
    .and(swir1.mask())
    .and(swir2.mask());

  var common = green
    .addBands(nir)
    .addBands(swir1)
    .addBands(swir2)
    .updateMask(valid);

  return addMetrics(common, image.select('Fmask'))
    .copyProperties(image, image.propertyNames())
    .set({
      sensor: 'L30',
      date_str:
        ee.Date(image.get('system:time_start'))
          .format('YYYY-MM-dd')
    });
}

function prepS30(image) {
  image = ee.Image(image);

  var green = image.select('B3').rename('green');
  var nir = image.select('B8A').rename('nir');
  var swir1 = image.select('B11').rename('swir1');
  var swir2 = image.select('B12').rename('swir2');

  var valid = qaMask(image)
    .and(green.mask())
    .and(nir.mask())
    .and(swir1.mask())
    .and(swir2.mask());

  var common = green
    .addBands(nir)
    .addBands(swir1)
    .addBands(swir2)
    .updateMask(valid);

  return addMetrics(common, image.select('Fmask'))
    .copyProperties(image, image.propertyNames())
    .set({
      sensor: 'S30',
      date_str:
        ee.Date(image.get('system:time_start'))
          .format('YYYY-MM-dd')
    });
}

function dailyMosaics(collection, sensor) {
  var dates = ee.List(
    collection.aggregate_array('date_str')
  ).distinct().sort();

  return ee.ImageCollection.fromImages(
    dates.map(function(dateStr) {
      dateStr = ee.String(dateStr);
      var day = collection.filter(
        ee.Filter.eq('date_str',dateStr)
      );

      return day.mosaic().set({
        date_str: dateStr,
        sensor: sensor,
        n_tiles: day.size(),
        'system:time_start':
          ee.Date(dateStr).millis()
      });
    })
  );
}

function exportYear(TARGET_YEAR) {
  var candidateYear = candidates
    .filter(
      ee.Filter.lte(
        'extract_start_year',TARGET_YEAR
      )
    )
    .filter(
      ee.Filter.gte(
        'extract_end_year',TARGET_YEAR
      )
    );

  var targetIds = ee.List(
    candidateYear.aggregate_array('Lake_ID_num')
  ).distinct();

  var targetInventory = inventory.filter(
    ee.Filter.inList('Lake_ID_num',targetIds)
  );

  var targetMask = ownership.remap({
    from: targetIds,
    to: ee.List.repeat(1,targetIds.size()),
    defaultValue: 0
  }).rename('target').selfMask();

  var targetZones =
    ownership.updateMask(targetMask);

  var startDate =
    ee.Date.fromYMD(TARGET_YEAR,START_MONTH,1);

  var endDate =
    ee.Date.fromYMD(TARGET_YEAR,END_MONTH,1)
      .advance(1,'month');

  var l30Raw = ee.ImageCollection(HLS_L30)
    .filterBounds(island)
    .filterDate(startDate,endDate)
    .map(prepL30);

  var s30Raw = ee.ImageCollection(HLS_S30)
    .filterBounds(island)
    .filterDate(startDate,endDate)
    .map(prepS30);

  var l30Daily = dailyMosaics(l30Raw,'L30');
  var s30Daily = dailyMosaics(s30Raw,'S30');

  function sceneLakeMetrics(image) {
    image = ee.Image(image);
    var zoneMask = targetZones.mask();

    var validArea = ee.Image.pixelArea()
      .updateMask(image.select('valid').mask())
      .rename('valid_area_m2');

    var aweiWaterArea = ee.Image.pixelArea()
      .updateMask(image.select('awei_water').eq(1))
      .rename('awei_water_area_m2');

    var mndwiWaterArea = ee.Image.pixelArea()
      .updateMask(image.select('mndwi_water').eq(1))
      .rename('mndwi_water_area_m2');

    var fmaskWaterArea = ee.Image.pixelArea()
      .updateMask(image.select('fmask_water').eq(1))
      .rename('fmask_water_area_m2');

    var sumImage = validArea
      .unmask(0).updateMask(zoneMask)
      .addBands(
        aweiWaterArea.unmask(0)
          .updateMask(zoneMask)
      )
      .addBands(
        mndwiWaterArea.unmask(0)
          .updateMask(zoneMask)
      )
      .addBands(
        fmaskWaterArea.unmask(0)
          .updateMask(zoneMask)
      )
      .addBands(targetZones);

    var groupedSum = ee.Dictionary(
      sumImage.reduceRegion({
        reducer: ee.Reducer.sum()
          .repeat(4)
          .group({
            groupField: 4,
            groupName: 'Lake_ID_num'
          }),
        geometry: island,
        crs: METRIC_CRS,
        scale: SCALE_M,
        maxPixels: 1e10,
        tileScale: 4
      })
    );

    var sumGroups = ee.List(
      ee.Algorithms.If(
        groupedSum.contains('groups'),
        groupedSum.get('groups'),
        ee.List([])
      )
    );

    var sumTable = ee.FeatureCollection(
      sumGroups.map(function(d) {
        d = ee.Dictionary(d);
        var sums = ee.List(d.get('sum'));

        return ee.Feature(null,{
          Lake_ID_num:
            d.get('Lake_ID_num'),
          valid_area_m2:sums.get(0),
          awei_water_area_m2:sums.get(1),
          mndwi_water_area_m2:sums.get(2),
          fmask_water_area_m2:sums.get(3)
        });
      })
    );

    var meanImage = image
      .select(['awei','mndwi'])
      .updateMask(zoneMask)
      .addBands(targetZones);

    var groupedMean = ee.Dictionary(
      meanImage.reduceRegion({
        reducer: ee.Reducer.mean()
          .repeat(2)
          .group({
            groupField: 2,
            groupName: 'Lake_ID_num'
          }),
        geometry: island,
        crs: METRIC_CRS,
        scale: SCALE_M,
        maxPixels: 1e10,
        tileScale: 4
      })
    );

    var meanGroups = ee.List(
      ee.Algorithms.If(
        groupedMean.contains('groups'),
        groupedMean.get('groups'),
        ee.List([])
      )
    );

    var meanTable = ee.FeatureCollection(
      meanGroups.map(function(d) {
        d = ee.Dictionary(d);
        var means = ee.List(d.get('mean'));
        return ee.Feature(null,{
          Lake_ID_num:d.get('Lake_ID_num'),
          mean_awei:means.get(0),
          mean_mndwi:means.get(1)
        });
      })
    );

    var sumsMeans = ee.FeatureCollection(
      ee.Join.saveFirst('mean_match').apply({
        primary:sumTable,
        secondary:meanTable,
        condition:ee.Filter.equals({
          leftField:'Lake_ID_num',
          rightField:'Lake_ID_num'
        })
      })
    );

    var joined = ee.FeatureCollection(
      ee.Join.saveFirst('inv_match').apply({
        primary:sumsMeans,
        secondary:targetInventory,
        condition:ee.Filter.equals({
          leftField:'Lake_ID_num',
          rightField:'Lake_ID_num'
        })
      })
    );

    var dateStr = image.get('date_str');
    var sensor = image.get('sensor');
    var nTiles = image.get('n_tiles');

    return joined
      .filter(ee.Filter.notNull(['inv_match']))
      .map(function(f) {
        f = ee.Feature(f);
        var inv =
          ee.Feature(f.get('inv_match'));

        var meanMatch = ee.Algorithms.If(
          ee.Algorithms.IsEqual(
            f.get('mean_match'),null
          ),
          null,
          f.get('mean_match')
        );

        var meanAwei = ee.Algorithms.If(
          ee.Algorithms.IsEqual(
            meanMatch,null
          ),
          null,
          ee.Feature(meanMatch)
            .get('mean_awei')
        );

        var meanMndwi = ee.Algorithms.If(
          ee.Algorithms.IsEqual(
            meanMatch,null
          ),
          null,
          ee.Feature(meanMatch)
            .get('mean_mndwi')
        );

        var ownershipM2 =
          ee.Number(
            inv.get('ownership_area_ha')
          ).multiply(10000);

        var validM2 =
          ee.Number(f.get('valid_area_m2'));

        var aweiM2 =
          ee.Number(
            f.get('awei_water_area_m2')
          );

        var mndwiM2 =
          ee.Number(
            f.get('mndwi_water_area_m2')
          );

        var fmaskM2 =
          ee.Number(
            f.get('fmask_water_area_m2')
          );

        return ee.Feature(null,{
          Lake_ID_num:f.get('Lake_ID_num'),
          Lake_ID:inv.get('Lake_ID'),
          date:dateStr,
          year:TARGET_YEAR,
          sensor:sensor,
          n_tiles:nTiles,

          ownership_area_ha:
            inv.get('ownership_area_ha'),
          reference_area_ha:
            inv.get('reference_area_ha'),

          valid_area_ha:
            validM2.divide(10000),
          valid_fraction:
            validM2.divide(ownershipM2),

          awei_water_area_ha:
            aweiM2.divide(10000),
          mndwi_water_area_ha:
            mndwiM2.divide(10000),
          fmask_water_area_ha:
            fmaskM2.divide(10000),

          awei_water_fraction_valid:
            ee.Algorithms.If(
              validM2.gt(0),
              aweiM2.divide(validM2),
              null
            ),

          mndwi_water_fraction_valid:
            ee.Algorithms.If(
              validM2.gt(0),
              mndwiM2.divide(validM2),
              null
            ),

          fmask_water_fraction_valid:
            ee.Algorithms.If(
              validM2.gt(0),
              fmaskM2.divide(validM2),
              null
            ),

          mean_awei:meanAwei,
          mean_mndwi:meanMndwi
        });
      })
      .filter(
        ee.Filter.gte(
          'valid_fraction',
          MIN_VALID_FRACTION
        )
      );
  }

  function collectionToTable(collection) {
    var n = collection.size();

    return ee.FeatureCollection(
      ee.Algorithms.If(
        n.gt(0),
        ee.FeatureCollection(
          ee.List.sequence(
            0,n.subtract(1)
          ).map(function(i) {
            return sceneLakeMetrics(
              ee.Image(
                collection.toList(n).get(i)
              )
            );
          })
        ).flatten(),
        ee.FeatureCollection([])
      )
    );
  }

  var l30Table =
    collectionToTable(l30Daily);

  var s30Table =
    collectionToTable(s30Daily);

  var combined =
    l30Table.merge(s30Table);

  print(
    'year',TARGET_YEAR,
    'candidate runs',
    candidateYear.size(),
    'distinct lakes',
    targetIds.size()
  );

  Export.table.toDrive({
    collection:combined,
    description:
      'SLI_HLS_ALLCAND_MarOct_' +
      TARGET_YEAR,
    fileNamePrefix:
      'SLI_HLS_ALLCAND_MarOct_' +
      TARGET_YEAR,
    fileFormat:'CSV'
  });
}

YEARS.forEach(exportYear);

Map.centerObject(islandFC,8);
