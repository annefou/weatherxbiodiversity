cwlVersion: v1.2
class: CommandLineTool

label: ERA5 retrieval (ECMWF ARCO store)
doc: |
  Streams hourly ERA5 single-level data from ECMWF's ARCO Zarr store and saves
  daily or monthly statistics (era5_retrieve.py). Any surface variable, any
  years from 1940, and either a box or the store tiles around occurrence points.
  Output files: era5_<var>_<stat>_monthly_<start>_<end>.nc (monthly) or
  era5_<var>_<stat>_daily_<year>.nc (daily), in ERA5's native units.
  Requests are paced and retried (the store rate-limits per CDS key).

hints:
  DockerRequirement:
    dockerImageId: era5_retrieval
    dockerFile:
      $include: Dockerfile
  SoftwareRequirement:
    packages:
      - package: python
        version: [ "3.12" ]

requirements:
  - class: InitialWorkDirRequirement
    listing:
      - entryname: era5_retrieve.py
        entry:
          $include: era5_retrieve.py
  - class: NetworkAccess
    networkAccess: true
  - class: InlineJavascriptRequirement

baseCommand: [python, era5_retrieve.py]

# One "--area N W S E" per box.
arguments:
  - valueFrom: |
      ${
        var args = [];
        (inputs.area || []).forEach(function (box) {
          args.push("--area");
          box.forEach(function (x) { args.push(String(x)); });
        });
        return args;
      }

inputs:
  variables:
    type: string
    default: '{"t2m": ["mean", "daily_min_mean", "daily_max_mean"], "tp": ["sum"]}'
    doc: |
      JSON {variable: [statistics]}. The default is what ERA5_Preprocessing needs
      (tmp, tmn, tmx, pre). Only the monthly files listed under outputs are
      returned as named outputs.
    inputBinding:
      prefix: --variables
  frequency:
    type:
      type: enum
      symbols: [monthly, daily]
    default: monthly
    doc: "monthly: mean, sum, daily_min_mean, daily_max_mean, daily_max_max; daily: mean, sum, min, max"
    inputBinding:
      prefix: --frequency
  years:
    type: int[]
    doc: "First and last year, e.g. [1940, 2014]"
    inputBinding:
      prefix: --years
  area:
    type:
      - "null"
      - type: array
        items:
          type: array
          items: float
    # Passed as "--area N W S E" once per box: see `arguments` below.
    doc: |
      One or more boxes [north, west, south, east] in degrees, e.g.
      [[44.8, -10.6, 34.3, 5.3], [30.2, -19.2, 26.6, -12.5]].
      Give either area or occurrences.
  occurrences:
    type: File?
    doc: "Optional alternative to area: occurrence table (tab-separated, decimalLatitude/decimalLongitude); only the store tiles around these points are read"
    inputBinding:
      prefix: --occurrences
  buffer:
    type: float?
    doc: "Degrees around the occurrences (default 1.0)"
    inputBinding:
      prefix: --buffer
  credentials_file:
    type: File
    doc: 'JSON {"key": "<CDS API key>"}'
    inputBinding:
      prefix: --credentials-file
  output_dir:
    type: string
    default: results
    inputBinding:
      prefix: --output-dir

# One named output per file (monthly frequency). Each is optional: it exists
# only if its variable/statistic was requested in `variables`.
outputs:
  t2m_mean:
    type: File?
    doc: Monthly mean 2 m temperature (K)
    outputBinding:
      glob: $(inputs.output_dir)/era5_t2m_mean_monthly_$(inputs.years[0])_$(inputs.years[1]).nc
  t2m_daily_min_mean:
    type: File?
    doc: Monthly mean of daily minimum 2 m temperature (K)
    outputBinding:
      glob: $(inputs.output_dir)/era5_t2m_daily_min_mean_monthly_$(inputs.years[0])_$(inputs.years[1]).nc
  t2m_daily_max_mean:
    type: File?
    doc: Monthly mean of daily maximum 2 m temperature (K)
    outputBinding:
      glob: $(inputs.output_dir)/era5_t2m_daily_max_mean_monthly_$(inputs.years[0])_$(inputs.years[1]).nc
  t2m_daily_max_max:
    type: File?
    doc: Monthly maximum of daily maximum 2 m temperature (K)
    outputBinding:
      glob: $(inputs.output_dir)/era5_t2m_daily_max_max_monthly_$(inputs.years[0])_$(inputs.years[1]).nc
  tp_sum:
    type: File?
    doc: Monthly total precipitation (m)
    outputBinding:
      glob: $(inputs.output_dir)/era5_tp_sum_monthly_$(inputs.years[0])_$(inputs.years[1]).nc


$namespaces:
  s: https://schema.org/

$schemas:
  - https://schema.org/version/latest/schemaorg-current-https.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0002-1784-2920
    s:name: Anne Fouilloux
