IF DB_ID('FMCG_Pipeline') IS NULL
    CREATE DATABASE FMCG_Pipeline;
GO

USE FMCG_Pipeline;
GO

IF SCHEMA_ID('raw') IS NULL        EXEC('CREATE SCHEMA raw');
IF SCHEMA_ID('curated') IS NULL    EXEC('CREATE SCHEMA curated');
IF SCHEMA_ID('quarantine') IS NULL EXEC('CREATE SCHEMA quarantine');
IF SCHEMA_ID('audit') IS NULL      EXEC('CREATE SCHEMA audit');
GO
