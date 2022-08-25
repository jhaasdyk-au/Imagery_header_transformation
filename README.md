# Imagery_header_transformation
Code for the datum transformation of Imagery header metadata. 
AVOID RESAMPLING Imagery as this is inefficient and can introduce errors.

Current state at time of repository creation (25 AUG 2022)
is detailed in Imagery_header_transform_README_2022mmdd.docx (20220825, 20220828)
An EXE (WINDOWS) as-is at 20220825 is also available from
https://www.dropbox.com/sh/qjv4k0numu0x6jl/AADXqq3BzvPXYqH9lCJUsHXya?dl=0

As of 25 AUG 2022, the code functions, but there is a lot which could be improved, as noted in the above.

INSTALL NOTES / HACKS
1)Installing GDAL (to satisfy nominal need for osgeo package) (WINDOWS)
https://opensourceoptions.com/blog/how-to-install-gdal-for-python-with-pip-on-windows
(Download the correct .whl file as indicated... e.g. GDAL-3.4.3-cp39-cp39-win_amd64.whl for Python 3.9    and so on)
(Preloaded a few whl and this URL instruction to folder HowToInstallGDAL)

2) If (1) above results in proj.DB errors (Version mismatch):
Note: Original code committed at 20220825 is hardcoded to look for a local proj.DB  
(Probably because this code was created with the intention of packaging into EXE??)
It would probably be best to re-code that (or investigate whether a local proj.db is necessary at all), but for a quick 
install as-is, copy the contents of the proj directory (i.e. the proj.db etc) which came with the GDAL install above.
    e.g. C:\Users\%USER%\AppData\Local\Programs\Python\Python39\Lib\site-packages\osgeo\data\proj
    into the proj folder in this Project.

3) Run the code with the parameters indicate in the exe usage or help, or as described at 
Imagery_header_transform_README_2022mmdd.docx Docs) (20220825, 20220828)

Success!

