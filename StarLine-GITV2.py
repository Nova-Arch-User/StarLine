import subprocess
import urllib.request
import urllib.error
import tarfile
import os
import sys
import json

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
  PackageToCheck = [PkgName]
  FoundDependencies = []
  while len(PackageToCheck) > 0:
    CurrentPkg = PackageToCheck.pop()
    FoundDependencies.append(CurrentPkg)
    UrlD = UrlD = f"https://aur.archlinux.org/rpc/v5/search/{PkgName}?by=name-desc"
    with urllib.request.urlopen(UrlD) as response:
     JsonString = response.read().decode('utf-8')
     PkgData = json.loads(JsonString)
    if PkgData.get("resultcount", 0) > 0:
        package_list = PkgData["results"]
        if package_list:
            Package_info = package_list[0]
            
            Depends = Package_info.get("Depends", [])
            MakeDepends = Package_info.get("MakeDepends", [])
            
            Dependencies = Depends + MakeDepends
            PackageToCheck.extend(Dependencies)
            print(f"Package '{CurrentPkg}' needs: {Dependencies}")
    else:
        print(f"No depen found for {CurrentPkg}")

            
  if PkgName in FoundDependencies:
      FoundDependencies.remove(PkgName)      
  for PkgName in FoundDependencies:
          download_AUR_Pkg(PkgName)
  OpenFile.close()
  os.remove(FileName)

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
     Ans = input("Would you like to read package build? y/N ")
     if Ans == "y":
      PkgBuild_Path = os.path.join(USER_CACHE_BASE, TargetPackage, "PKGBUILD")
      with open(PkgBuild_Path, "r") as file_stream:
          print(file_stream.read())
      Ans = input("Would you like to procede? y/N ")
      if Ans != "y":
       break
     ExtractedFolderPath = os.path.join(USER_CACHE_BASE, TargetPackage)
     BuildPackage(ExtractedFolderPath)
     print("Download complete!")
     break
   else:
     print("Please enter a valid package name")
  except KeyboardInterrupt:
   print("Terminated")
   break