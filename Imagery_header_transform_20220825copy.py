#!/usr/bin/env python3
"""
Tool builds a pipeline to convert datasets between GDA94 datum and GDA2020
through metadata operations only. This script was intended for small translations
of the reference area only.
Overwrites or creates new datasets in option

Usage:
    python3 shift_datum.py file1.tif
    python3 shift_datum.py file1.pdf
    python3 shift_datum.py "folder"

    python3 shift_datum.py file1.pdf -newdir "new directory"  -s_srs "EPSG:28357" -t_srs "EPSG:7857"

Extensions:
    * support folder and sub folder input
    * support relative folder input
    * Options for input srs and output srs
    * Apply to datasets referenced with GCPs
    * Adapting the best transformer from the 4326 -> 7844 transformer group
    * Improved selection of output CRS (currently only matches on MGA or datum)

Note: Decision has to be made about Proprietary sidecar Georeference files;
    * Some information is available: https://gdal.org/drivers/raster/gtiff.html#georeferencing
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional
import shutil
import pyproj.transformer
from osgeo import gdal, osr
from pyproj.database import query_crs_info;
from pyproj.enums import PJType;

projlib=os.path.abspath(os.getcwd())+"\proj"
os.environ["PROJ_LIB"] = projlib
GDA2020_GEODETIC = pyproj.crs.CRS.from_epsg(7844)
GDA94_GEODETIC = pyproj.crs.CRS.from_epsg(4283)
CONFORMAL_DISTORTION = "GDA94 to GDA2020 (2)"
pyproj.network.set_network_enabled(True)
gdal.UseExceptions()
osr.UseExceptions()

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


def get_proj_transformer(
        gda94: pyproj.crs.CRS,
        gda2020: pyproj.crs.CRS,
        transformer_lookup: str=CONFORMAL_DISTORTION,
        ) -> pyproj.transformer.Transformer:
    """
    Creates a proj pipeline to transform coordinates.
    Pipeline steps:
        * to project coordinates in EPSG:4283 from input
        * to project from EPSG:4283 to EPSG:7844
        * to project coordinates from EPSG:7844 to output
    """
    #pyproj.transformer.TransformerGroup(GDA94_GEODETIC, GDA2020_GEODETIC)
    transformer = pyproj.transformer.Transformer.from_pipeline(transformer_lookup)
    pipeline_prefix = len("+proj=pipeline")

    # Create pipeline to convert from source CRS to 4283
    from_projected = ""
    if gda94 != GDA94_GEODETIC:
        from_projected = pyproj.transformer.Transformer.from_crs(crs_from=gda94, crs_to=GDA94_GEODETIC).to_proj4()[pipeline_prefix:]

    project = transformer.to_proj4()[pipeline_prefix:]
    # Create pipeline to convert from 7844 to destination CRS
    to_projected = ""
    if gda2020 != GDA2020_GEODETIC:
        to_projected = pyproj.transformer.Transformer.from_crs(crs_from=GDA2020_GEODETIC, crs_to=gda2020).to_proj4()[pipeline_prefix:]

    return pyproj.transformer.Transformer.from_pipeline(f"""\
+proj=pipeline
  {from_projected}
  {project}
  {to_projected}
""")


def get_output_crs(filter_term: str) -> pyproj.crs.CRS:
    """ Returns an output CRS based on name filters; useful for corresponding GDA2020 MGA projections """
    partials = []
    for crs in query_crs_info(auth_name="EPSG",pj_types=PJType.PROJECTED_CRS):
        if filter_term == crs.name:
            return pyproj.crs.CRS.from_epsg(crs.code)
        elif filter_term in crs.name:
            partials.append(crs)

    if len(partials) == 1:
        return pyproj.crs.CRS.from_epsg(partials[0].code)
    raise NotImplementedError(f"More than one partial CRS match for filter term: {filter_term}")


def check_grids(source: pyproj.crs.CRS=GDA94_GEODETIC, dest: pyproj.crs.CRS=GDA2020_GEODETIC) -> None:
    """ Checks that the conformal grids are available """
    tg = pyproj.transformer.TransformerGroup(source, dest)
    if tg.unavailable_operations:
        logging.info("Downloading transformation grids for: {source.name}->{dest.name}")
        tg.download_grids(verbose=True)
    if tg.unavailable_operations:
        raise NotImplementedError("Recovery from unavailable operations required")


def transform_boundaries(
        fn: Path,
        crs_from: Optional[pyproj.crs.CRS]=None,
        crs_to: Optional[pyproj.crs.CRS]=None) -> Path:
    """ Updates dataset spatial reference and bounds """
    ds = gdal.Open(str(fn), gdal.GA_ReadOnly)

    try:
        if not crs_from:
            sr = ds.GetSpatialRef()
            # Standardises projection definition to authority definitions
            crs_from = pyproj.crs.CRS.from_user_input(
                pyproj.crs.CRS.from_wkt(sr.ExportToWkt()).to_authority()
            )

        # breakpoint()
        if not crs_to:
            if crs_from.geodetic_crs.name == GDA94_GEODETIC.name:
                crs_to = get_output_crs(crs_from.name.replace("GDA94", "GDA2020"))
            elif crs_from.geodetic_crs.name == GDA2020_GEODETIC.name:
                crs_to = get_output_crs(crs_from.name.replace("GDA2020", "GDA94"))
            else:
                raise NotImplementedError("Only GDA94 and GDA2020 are accepted")

        if crs_from:
            logging.info(f"From CRS was determined to be: {crs_from.name}")
        if crs_to:
            logging.info(f"Converting to CRS: {crs_to.name}")

        if crs_to.geodetic_crs == crs_from.geodetic_crs:
            logging.warning(f"{fn} already in correct datum: {crs_to.name}")
            return fn

        if ds.GetGCPCount() > 0:
            raise NotImplementedError("Need to transform and update GCPs")



        width, height = ds.RasterXSize, ds.RasterYSize
        src_transform = ds.GetGeoTransform()
        # check if it is inside grid
        if 552501.9300458187<= src_transform[0] <=584296.3888727566:#Christmas Island - onshore
            CONFORMAL_DISTORTION="GDA94 to GDA2020 (4)"
        elif 256344.16261634606<= src_transform[0] <=280960.09420572605:
            CONFORMAL_DISTORTION = "GDA94 to GDA2020 (5)"#Cocos (Keeling) Islands
        elif src_transform[0]>=575472.4077616993 or src_transform[0]<=702381.9637579136:
            CONFORMAL_DISTORTION = "GDA94 to GDA2020 (1)"


        direction = pyproj.enums.TransformDirection.FORWARD
        if crs_from.geodetic_crs.name == GDA94_GEODETIC.name:
            transformer = get_proj_transformer(gda94=crs_from, gda2020=crs_to,transformer_lookup=CONFORMAL_DISTORTION)
        else:
            direction = pyproj.enums.TransformDirection.INVERSE
            transformer = get_proj_transformer(gda94=crs_to, gda2020=crs_from,transformer_lookup=CONFORMAL_DISTORTION)
            if not transformer.has_inverse:
                raise NotImplementedError("Generated transform has no inverse")


        # Taken from gdal_move.py
        # Src: https://github.com/OSGeo/gdal/blob/aead0f037 07d3717331987cd02f2d0a74ffdafd2/gdal/swig/python/gdal-utils/osgeo_utils/gdalmove.py
        corners_names = [
            'Upper Left', 'Lower Left', 'Upper Right', 'Lower Right', 'Center'
        ]
        corner_pixels = [
            (0, 0, 0),
            (0, height, 0),
            (width, 0, 0),
            (width, height, 0),
            (width / 2.0, height / 2.0, 0)
        ]
        src_corners = []
        for coord in corner_pixels:
            src_corners.append((
                src_transform[0] + coord[0] * src_transform[1] + coord[1] * src_transform[2],
                src_transform[3] + coord[0] * src_transform[4] + coord[1] * src_transform[5],
                coord[2]
            ))

        new_ul = transformer.transform(*src_corners[0], direction=direction,errcheck=True)
        new_ur = transformer.transform(*src_corners[2], direction=direction,errcheck=True)
        new_ll = transformer.transform(*src_corners[1], direction=direction,errcheck=True)

        new_trans = (
            new_ul[0],
            (new_ur[0] - new_ul[0]) / width,
            (new_ll[0] - new_ul[0]) / height,
            new_ul[1],
            (new_ur[1] - new_ul[1]) / width,
            (new_ll[1] - new_ul[1]) /height
        )

        new_sr = osr.SpatialReference()
        new_sr.ImportFromEPSG(crs_to.to_epsg())

        del ds  # Close file handle


        ds = gdal.Open(str(fn), gdal.GA_Update)
        ds.SetProjection(new_sr.ExportToWkt())
        ds.SetGeoTransform(new_trans)


        # For information on overviews read: https://gdal.org/drivers/raster/gtiff.html#overviews
        # ds.BuildOverviews()
        del ds  # Save file

        logging.info(f"Completed writing metadata for {str(fn)}")
        return fn
    except Exception:
        logging.exception('Cathched exception:'+str(Exception))
        return False

def copycurfile(
        filepath: Path,
        copyflag: bool,
        newdir: Optional[str]=None)-> Path:
    if copyflag==True:
        if not os.path.exists(os.path.dirname(filepath)+"\\"+newdir+"\\"):
            os.mkdir(os.path.join(os.path.dirname(filepath),newdir))

        newfilepath =os.path.join(os.path.dirname(filepath)+"\\"+newdir+"\\",os.path.basename(filepath))
        shutil.copy(str(filepath),str(newfilepath))
        return newfilepath
    else:
        return filepath

def cli():
    """ command line entrypoint to shift datum script """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-s_srs", type=pyproj.crs.CRS.from_user_input, required=False)
    parser.add_argument("-t_srs", type=pyproj.crs.CRS.from_user_input, required=False)
    parser.add_argument("dir", help="specify the Directory containing geoPDF or Tiff files")
    parser.add_argument("-newdir", help="specify the sub Directory , optional")
    args = parser.parse_args()
    if args.dir:
        check_grids()  # Check that transformation grids available
        if os.path.isdir(args.dir):
            subdirs = os.listdir(args.dir)
            for subdir in subdirs:
                subdir=os.path.join(args.dir,subdir)
                if os.path.isdir(subdir):
                    fs = os.listdir(subdir)
                    for fe in fs:
                        filetype = os.path.splitext(fe)[-1]
                        if filetype.lower() in ['.tif','.pdf']:
                            filepath = Path(os.path.join(subdir, fe))
                            if not os.access(filepath.resolve(), os.O_RDWR):  # check if file read/writable
                                logging.error(f"Unable to read or write to {filepath.resolve()}")
                                sys.exit(1)
                            logging.info(f"Processing: {fe}")
                            if args.newdir:
                                newfilepath = copycurfile(filepath, True,args.newdir)
                            else:
                                newfilepath = copycurfile(filepath,False)

                            transform_boundaries(newfilepath, crs_from=args.s_srs, crs_to=args.t_srs)
                        else:
                            logging.error(f"Not a supported file: {fe}")
                else:
                   fe=subdir
                   filetype = os.path.splitext(fe)[-1]
                   if filetype.lower() in ['.tif', '.pdf']:
                       filepath = Path(fe)
                       if not os.access(filepath.resolve(), os.O_RDWR):  # check if file read/writable
                           logging.error(f"Unable to read or write to {filepath.resolve()}")
                           sys.exit(1)
                       logging.info(f"Processing: {fe}")
                       if args.newdir:
                           newfilepath = copycurfile(filepath, True, args.newdir)
                       else:
                           newfilepath = copycurfile(filepath, False)

                       transform_boundaries(newfilepath, crs_from=args.s_srs, crs_to=args.t_srs)
                   else:
                       logging.error(f"Not a supported file: {fe}")
        else:
             # Save file



            filepath =  Path(args.dir)

            filetype = os.path.splitext(filepath)[-1]
            if filetype.lower() in ['.tif','.pdf' ,'.ecw']:

                if not os.access(filepath.resolve(), os.O_RDWR):  # check if file read/writable
                    logging.error(f"Unable to read or write to {filepath.resolve()}")
                    sys.exit(1)
                logging.info(f"Processing: {filepath}")
                if args.newdir:
                    newfilepath = copycurfile(filepath, True, args.newdir)
                else:
                    newfilepath = copycurfile(filepath, False)

                transform_boundaries(newfilepath, crs_from=args.s_srs, crs_to=args.t_srs)
            else:
                logging.error(f"Not a supported file: {filepath}")
    else:
        logging.warning("No files provided")


if __name__ == "__main__":
    cli()
