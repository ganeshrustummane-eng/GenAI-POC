CREATE TABLE DevT5000.dbo.Addresses (
	AddressID int IDENTITY(1,1) NOT NULL,
	SiteID int NOT NULL,
	sMrMrs nvarchar(4) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	sFName nvarchar(25) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	sMI nvarchar(2) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	sLName nvarchar(25) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
	sCompany nvarchar(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	sAddr1 nvarchar(40) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
	sAddr2 nvarchar(40) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	sCity nvarchar(25) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
	sRegion nvarchar(25) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	sPostalCode nvarchar(10) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	sCountry nvarchar(15) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
	sPhone1 nvarchar(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	sPhone2 nvarchar(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	sPhone3 nvarchar(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	sPhone4 nvarchar(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	sPhone5 nvarchar(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	sPhone6 nvarchar(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	dcLongitude decimal(18,10) NULL,
	dcLatitude decimal(18,10) NULL,
	bPermanent bit DEFAULT 0 NOT NULL,
	dDeleted datetime NULL,
	dUpdated datetime DEFAULT getdate() NOT NULL,
	dArchived datetime NULL,
	uTS timestamp NOT NULL,
	OldPK int NULL,
	CONSTRAINT PK_Addresses PRIMARY KEY (AddressID)
);
 CREATE NONCLUSTERED INDEX IX_Addresses_SiteID_dUpdated ON DevT5000.dbo.Addresses (  SiteID ASC  , dUpdated ASC  )  
	 INCLUDE ( AddressID , bPermanent , dArchived , dcLatitude , dcLongitude , dDeleted , OldPK , sAddr1 , sAddr2 , sCity , sCompany , sCountry , sFName , sLName , sMI , sMrMrs , sPhone1 , sPhone2 , sPhone3 , sPhone4 , sPhone5 , sPhone6 , sPostalCode , sRegion , uTS ) 
	 WITH (  PAD_INDEX = OFF ,FILLFACTOR = 100  ,SORT_IN_TEMPDB = OFF , IGNORE_DUP_KEY = OFF , STATISTICS_NORECOMPUTE = OFF , ONLINE = OFF , ALLOW_ROW_LOCKS = ON , ALLOW_PAGE_LOCKS = ON  )
	 ON [PRIMARY ] ;


DROP TABLE IF EXISTS #Addresses_Raw;

CREATE TABLE #Addresses_Raw
(
    AddressID    varchar(50),
    SiteID       varchar(50),
    sMrMrs       varchar(100),
    sFName       varchar(200),
    sMI          varchar(100),
    sLName       varchar(200),
    sCompany     varchar(200),
    sAddr1       varchar(300),
    sAddr2       varchar(300),
    sCity        varchar(200),
    sRegion      varchar(200),
    sPostalCode  varchar(100),
    sCountry     varchar(200),
    sPhone1      varchar(200),
    sPhone2      varchar(200),
    sPhone3      varchar(200),
    sPhone4      varchar(200),
    sPhone5      varchar(200),
    sPhone6      varchar(200),
    dcLongitude  varchar(100),
    dcLatitude   varchar(100),
    bPermanent   varchar(50),
    dDeleted     varchar(100),
    dUpdated     varchar(100),
    dArchived    varchar(100),
    uTS          varchar(200),
    OldPK        varchar(50)
);


BULK INSERT #Addresses_Raw
FROM 'C:\EPAM-Personal\Migration-validator\MSServer-data\Addresses_mssqlserver.csv'
WITH
(
    FORMAT = 'CSV',
    FIRSTROW = 2,
    FIELDQUOTE = '"',
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '0x0a'
);


SET IDENTITY_INSERT DevT5000.dbo.Addresses ON;

INSERT INTO DevT5000.dbo.Addresses
(
    AddressID,
    SiteID,
    sMrMrs,
    sFName,
    sMI,
    sLName,
    sCompany,
    sAddr1,
    sAddr2,
    sCity,
    sRegion,
    sPostalCode,
    sCountry,
    sPhone1,
    sPhone2,
    sPhone3,
    sPhone4,
    sPhone5,
    sPhone6,
    dcLongitude,
    dcLatitude,
    bPermanent,
    dDeleted,
    dUpdated,
    dArchived,
    OldPK
)
SELECT
    TRY_CONVERT(int, AddressID),
    TRY_CONVERT(int, SiteID),
    sMrMrs,
    sFName,
    sMI,
    sLName,
    sCompany,
    COALESCE(NULLIF(LTRIM(RTRIM(sAddr1)), ''), 'Unknown'),
    sAddr2,
    COALESCE(NULLIF(LTRIM(RTRIM(sCity)), ''), 'Unknown'),
    sRegion,
    sPostalCode,
    COALESCE(NULLIF(LTRIM(RTRIM(sCountry)), ''), 'Unknown'),
    sPhone1,
    sPhone2,
    sPhone3,
    sPhone4,
    sPhone5,
    sPhone6,
    TRY_CONVERT(decimal(18,10), NULLIF(dcLongitude, '')),
    TRY_CONVERT(decimal(18,10), NULLIF(dcLatitude, '')),
    TRY_CONVERT(bit, NULLIF(bPermanent, '')),
    TRY_CONVERT(datetime, NULLIF(dDeleted, '')),
    TRY_CONVERT(datetime, NULLIF(dUpdated, '')),
    TRY_CONVERT(datetime, NULLIF(dArchived, '')),
    TRY_CONVERT(int, NULLIF(OldPK, ''))
FROM #Addresses_Raw;

SET IDENTITY_INSERT DevT5000.dbo.Addresses OFF;

select * from DevT5000.dbo.Addresses;


SELECT *
FROM #Addresses_Raw
WHERE NULLIF(LTRIM(RTRIM(sCountry)), '') IS NULL;


SELECT
    @@SERVERNAME AS server_name,
    DB_NAME() AS database_name,
    CONNECTIONPROPERTY('net_transport') AS transport,
    CONNECTIONPROPERTY('local_tcp_port') AS tcp_port,
    CONNECTIONPROPERTY('auth_scheme') AS auth_scheme,
    SUSER_SNAME() AS login_name;