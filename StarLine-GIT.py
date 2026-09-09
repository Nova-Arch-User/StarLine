import subprocess
import urllib.request
import urllib.error
import tarfile
import os
import sys

def BuildPackage(DirPath):
  subprocess.run(["makepkg", "-si"], cwd=DirPath, check=True)

USER_CACHE_BASE = os.path.join(os.path.expanduser("~"), ".cache", "StarLine")

def download_AUR_Pkg(PkgName):
 try:
  pkg_cache_dir = os.path.join(USER_CACHE_BASE, PkgName)
  os.makedirs(pkg_cache_dir, exist_ok=True)
  Url = f"https://aur.archlinux.org/cgit/aur.git/snapshot/{PkgName}.tar.gz"
  FileName = os.path.join(pkg_cache_dir, f"{PkgName}.tar.gz")
  print(f"Downloading {PkgName}...")
  urllib.request.urlretrieve(Url, FileName)
  OpenFile = tarfile.open(FileName)
  OpenFile.extractall(path=USER_CACHE_BASE)
  OpenFile.close()
  os.remove(FileName)
  Ans = input("Would you like to read package build? y/N ")
  if Ans == "y":
        PkgBuild_Path = os.path.join(USER_CACHE_BASE, PkgName, "PKGBUILD")
        with open(PkgBuild_Path, "r") as file_stream:
         print(file_stream.read())
        return True   
 except urllib.error.HTTPError as e:
   if e.code == 404:
     print("This package could not be found")
     sys.exit()
   else:
     print(f"Server error, could not connect: {e.code} {e.reason}") 
     sys.exit()


if __name__ =="__main__":
 TargetPackage = input("Please enter PkgName: ").strip()
while True:
 try:
   if TargetPackage:
    download_AUR_Pkg(TargetPackage)
    ExtractedFolderPath = os.path.join(USER_CACHE_BASE, TargetPackage)
    BuildPackage(ExtractedFolderPath)
    print("Download complete!")
    break
   else:
    print("Please enter a valid package name")
 except KeyboardInterrupt:
   print("Terminated")
   break