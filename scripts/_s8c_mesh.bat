@echo off
cd /d C:\Users\vibhe\Downloads\OUTPUT\CFD
if "%S8C%"=="" set S8C=wedge stator rotor
for %%G in (%S8C%) do (
  .venv\Scripts\python -I scripts\u666_mesh.py --solids --group %%G > mesh\u666\s8c_%%G.log 2>&1
)
echo done > mesh\u666\s8c_done.txt
