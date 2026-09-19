import subprocess
import urllib.request
import urllib.error
import tarfile
import os
import sys
import json
import re  
import shutil
from collections import defaultdict, deque 

def BuildPackage(DirPath):
    
     command = ["makepkg", "-si", "--noconfirm"]
     subprocess.run(command, cwd=DirPath, check=True)

USER_CACHE_BASE = os.path.join(os.path.expanduser("~"), ".cache", "StarLine")

class KahnGraph:
   def __init__(self, n):
      self.n = n
      self.graph = defaultdict(list)
      self.InDegree = [0] * n

   def DrawEdge(self, u, v):
      self.graph[u].append(v)
      self.InDegree[v] += 1

   
   def KahnSort(Dependency):
    N = len(Dependency)
    indegree = [0] * N
    result = []
    queue = deque()

    for i in range (N):
     for NextNode in Dependency[i]:
       indegree[NextNode] += 1
    for i in range(N):
     if indegree[i] == 0:
       queue.append(i)
    while queue:
     top = queue.popleft()
     result.append(top)
     for NextNode in Dependency[top]:
       indegree[NextNode] -= 1
       if indegree[NextNode] == 0:
          queue.append(NextNode)
    return result  

def download_AUR_Pkg(PkgName, IsMainPackage=True):
 AnsB = "y"
  
 try:
  pkg_cache_dir = os.path.join(USER_CACHE_BASE, PkgName)
  if os.path.exists(pkg_cache_dir):
     shutil.rmtree(pkg_cache_dir)
  os.makedirs(pkg_cache_dir, exist_ok=True)
  
  Url = f"https://aur.archlinux.org/cgit/aur.git/snapshot/{PkgName}.tar.gz"
  FileName = os.path.join(pkg_cache_dir, f"{PkgName}.tar.gz")
  
  print(f"Downloading {PkgName}...")
  urllib.request.urlretrieve(Url, FileName)
  OpenFile = tarfile.open(FileName)
  if IsMainPackage:
       
       Ans = input("Would you like to read package build? y/N ")
       if Ans == "y":
      
        with tarfile.open(FileName, "r:gz") as OpenFile:
         AllFiles = OpenFile.getnames()
         for File in AllFiles:
          if File == f"{PkgName}/PKGBUILD":
             OpenFile.extract(File, USER_CACHE_BASE)
             PkgBuild_Path = os.path.join(USER_CACHE_BASE, File)
             break   
        with open(PkgBuild_Path, "r") as file_stream:
         print(file_stream.read())
         AnsB = input("Would you like to procede? y/N ")
         if AnsB != "y":
            
            return False
  OpenFile = tarfile.open(FileName)
  OpenFile.extractall(path=USER_CACHE_BASE)
  OpenFile.close()
  os.remove(FileName)
  ExtractedFolderPath = os.path.join(USER_CACHE_BASE, PkgName)
  BuildPackage(ExtractedFolderPath)

 except urllib.error.HTTPError as e:
    if e.code == 404:
      if IsMainPackage:
            print("This package could not be found")
            return False
            
      else:
            print(f"Skipping '{PkgName}': not on AUR, probably an official repo package")
            return
    else:
      print(f"Server error, could not connect: {e.code} {e.reason}") 
      return False

def DownloadDependencies(PkgName):
   PackageToCheck = [PkgName]
   FoundDependencies = []
   Seen = {PkgName}
   
   while len(PackageToCheck) > 0:
       CurrentPkg = PackageToCheck.pop()
       Seen.add(CurrentPkg)
       Arch_Repo_Check = subprocess.run(["pacman", "-Si", CurrentPkg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
       if Arch_Repo_Check.returncode == 0:
          continue
       UrlD = f"https://aur.archlinux.org/rpc/v5/info/{CurrentPkg}"
       
       try:
           with urllib.request.urlopen(UrlD) as response:
            JsonString = response.read().decode('utf-8')
            PkgData = json.loads(JsonString)
       except Exception:
           continue
           
       if PkgData.get("resultcount", 0) > 0:
           package_list = PkgData["results"]
           if package_list:
               FoundDependencies.append(CurrentPkg)
               Package_info = package_list[0]
               Depends = Package_info.get("Depends", [])
               MakeDepends = Package_info.get("MakeDepends", [])
               
               Depends = Cleaner(Depends)
               MakeDepends = Cleaner(MakeDepends)
               Dependencies = Depends + MakeDepends
               
               NewDeps = [d for d in Dependencies if d not in Seen and d] 
               for d in NewDeps:
                  Seen.add(d)
               PackageToCheck.extend(NewDeps)
               print(f"Package '{CurrentPkg}' needs: {Dependencies}")
       else:
           print(f"No depen found for {CurrentPkg}")

           

   if PkgName in FoundDependencies:
      FoundDependencies.remove(PkgName)      
   return FoundDependencies

def Cleaner(RawData):
   CleanList = []
   for Data in RawData:
   
      CleanData = re.split(r'[=><:]', Data)[0].strip()
      if CleanData:
         CleanList.append(CleanData)
   return CleanList

      
   

if __name__ =="__main__":
 TargetPackage = input("Please enter PkgName: ").strip()
 while True:
  try:
   if TargetPackage:
     depenChoice = input("Would you like to download the AUR dependencies? Y/n").strip()
     if depenChoice == "Y":
      FoundDepends = DownloadDependencies(TargetPackage)
      Kahn = KahnGraph(len(FoundDepends))
      Kahn.DrawEdge(FoundDepends, TargetPackage)
      Kahn.KahnSort(FoundDepends[0])
      FoundDepends.append(TargetPackage) 
      for Depend in FoundDepends:
         Is_Installed = subprocess.run(["pacman", "-Qq", Depend], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
         if Is_Installed.returncode == 0:
            print(f"Skipped, dependency: {Depend} already installed")
            pass
         else:
            try: 
             subprocess.run(["sudo", "pacman", "-S", "--noconfirm", Depend], check=True)
             print(f"Dependency: {Depend} installed from official Arch repo!")
            except: 
             is_target = (Depend == TargetPackage)
             download_AUR_Pkg(Depend, is_target)
             
     if download_AUR_Pkg:
      print("Download and installation complete!")
      break
     else:
      break
   else:
     print("Please enter a valid package name")
  except KeyboardInterrupt:
   print("Terminated")
   break
  