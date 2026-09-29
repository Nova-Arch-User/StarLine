import subprocess
import urllib.request
import urllib.error
import tarfile
import os
import json
import re  
import shutil
from collections import defaultdict, deque 

def BuildPackage(DirPath):
    
     command = ["makepkg", "-si"]
     subprocess.run("pwd")
     subprocess.run(command, cwd=DirPath, check=True)

USER_CACHE_BASE = os.path.join(os.path.expanduser("~"), ".cache", "StarLine")

class KahnGraph:
   def __init__(self):
      
      self.graph = defaultdict(list)
      self.InDegree = defaultdict(int)

   def DrawEdge(self, u, v):
      self.graph[u].append(v)
      self.InDegree[v] += 1

   
   def KahnSort(self):
    
    indegree = self.InDegree
    result = []
    queue = deque()

    all_pkgs = set(list(self.graph.keys()) + list(self.InDegree.keys()))

    for pkg in all_pkgs:
     if indegree[pkg] == 0:
       queue.append(pkg)
    while queue:
     top = queue.popleft()
     result.append(top)
     for NextNode in self.graph[top]:
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
  return True
 except urllib.error.HTTPError as e:
    if e.code == 404:
      if IsMainPackage:
            print("This package could not be found")
            return False
    else:
      print(f"Server error, could not connect: {e.code} {e.reason}") 
      return False

def DownloadDependencies(PkgName, Kahn):
   PackageToCheck = [PkgName]
   FoundDependencies = []
   Seen = set()
   while len(PackageToCheck) > 0:
       CurrentPkg = PackageToCheck.pop()
       if CurrentPkg in Seen:
         continue
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
               

               Package_info = package_list[0]
               Depends = Package_info.get("Depends", [])
               MakeDepends = Package_info.get("MakeDepends", [])
               OptDepends = Package_info.get("OptDepends", [])
               
               Depends = Cleaner(Depends)
               MakeDepends = Cleaner(MakeDepends)
               Dependencies = Depends + MakeDepends + OptDepends
               
               NewDeps = [d for d in Dependencies if d not in Seen and d] 
               for d in NewDeps:
                  Kahn.DrawEdge(d, CurrentPkg)
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
  Kahn = KahnGraph()
  Comp = True
  try:
   
   if TargetPackage:
      
      FoundDepends = DownloadDependencies(TargetPackage, Kahn)
      IndexedDepends = {Idx: Value for Idx, Value in enumerate(FoundDepends)}
      FinalDepenList = Kahn.KahnSort() 
      
      for Depend in FinalDepenList:
         if Depend == TargetPackage:
           continue
         Is_Installed = subprocess.run(["pacman", "-T", Depend], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
         if Is_Installed.returncode == 0:
            print(f"Skipped, dependency: {Depend} already installed")
            pass
         else:
            try: 
             subprocess.run(["sudo", "pacman", "-S", "--noconfirm", Depend], check=True)
             print(f"Dependency: {Depend} installed from official Arch repo!")
            except:
               is_target = (Depend == TargetPackage)
               if is_target == True:
                 continue

               Comp = download_AUR_Pkg(Depend, is_target)
               if not Comp:
                print(f"Failed to build AUR package: {Depend}")
                break


      if Comp:
       Comp = download_AUR_Pkg(TargetPackage, IsMainPackage=True)
      if Comp:
       print("Download and installation complete!")
       break
   
   else:
     print("Please enter a valid package name")
     break
  except KeyboardInterrupt:
   print("Terminated")
   break
  