# 🧠 Sistema de Recomendación de Candidatos (PMV)

Este proyecto implementa un sistema de recomendación de personal basado en IA, desarrollado con **FastAPI**, **Streamlit**, **MongoDB Atlas** y **Docker Compose**.

## 🚀 Arquitectura
- **Frontend:** Streamlit (interfaz para reclutadores y candidatos)
- **Backend:** FastAPI (servicios REST + JWT + embeddings + ranking)
- **Base de Datos:** MongoDB Atlas (almacenamiento de perfiles, CVs y rankings)
- **Despliegue:** Docker Compose (multi-servicio: frontend + backend)

## 🧩 Funcionalidades Principales
- Registro y autenticación de usuarios (JWT)
- Carga y análisis automático de CV (PDF)
- Extracción de texto + embeddings semánticos
- Comparación y ranking de candidatos por perfil
- Panel de métricas y visualización

## 🛠️ Ejecutar con Docker
