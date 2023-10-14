DROP TABLE IF EXISTS vminfo;

CREATE TABLE vminfo (
    name TEXT NOT NULL,
    ip TEXT NOT NULL,
    cpu TEXT NOT NULL,
    ram TEXT NOT NULL,
    disk TEXT NOT NULL,
    status TEXT NOT NULL,
    uptime REAL NOT NULL,
    cpuusage REAL NOT NULL,
    ramusage REAL NOT NULL,
    netusage REAL NOT NULL,
    measuretime DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (name, measuretime)
);

CREATE INDEX name_measuretime ON vminfo (name, measuretime);
