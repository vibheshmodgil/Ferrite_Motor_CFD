from paraview.simple import *
r = OpenFOAMReader(FileName=r"\wsl.localhost\Ubuntu-24.04\home\cfd\cfd\peak_torque\case.foam")
r.CaseType = "Decomposed Case"
r.UpdatePipelineInformation()
print("times", r.TimestepValues)
print("regions", r.GetProperty("MeshRegions").Available[:40] if hasattr(r.GetProperty("MeshRegions"), "Available") else r.MeshRegions)
print(r.ListProperties())
