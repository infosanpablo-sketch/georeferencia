#!/bin/bash
# Run this inside the project root (the folder that contains app.py)
ZIPNAME="asistencia_geo.zip"
echo "Creating ${ZIPNAME} ..."
zip -r "${ZIPNAME}" . -x "__pycache__/*" "*.pyc" ".git/*" "venv/*" "asistencia.db" ".env" "${ZIPNAME}"
echo "Done: ${ZIPNAME}"