# Imagery_header_transformation
Code for the datum transformation of Imagery header metadata. 
AVOID RESAMPLING Imagery as this is inefficient and can introduce errors.

Current state at time of repository creation (25 AUG 2022)
is detailed in Imagery_header_transform_README_20220825.docx
An EXE (WINDOWS) as at state 20220825.docx is also available from
https://www.dropbox.com/sh/qjv4k0numu0x6jl/AADXqq3BzvPXYqH9lCJUsHXya?dl=0

As of 25 AUG 2022, the code functions, but there is a lot which could be improved, as noted in the above.

INSTALL NOTES / HACKS
1)Installing GDAL (or GDAL instead of osgeo package)
https://opensourceoptions.com/blog/how-to-install-gdal-for-python-with-pip-on-windows/#:~:text=How%20to%20Install%20GDAL%20for%20Python%20with%20pip,file%20with%20pip.%203%203.%20Test%20the%20installation.
(Download the correct .whl file as indicated... e.g. GDAL-3.4.3-cp39-cp39-win_amd64.whl for Python 3.9    and so on)
(Preloaded a few whl and this URL instruction to folder HowToInstallGDAL)

2) PROJ DB no longer matched.
Code at 20220825 is hardcoded to look for a local proj.DB  (because this was made to packed into EXE?)
Probably best to recode that, but on first instance copy the proj.db that came with the GDAL install,
   (in fact, copy all the contents of the proj directory)
C:\Users\%USER%\AppData\Local\Programs\Python\Python39\Lib\site-packages\osgeo\data\proj
into the proj folder in this Project.

3) Success!

