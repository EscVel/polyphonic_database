CREATE DATABASE IF NOT EXISTS POLYPHONIC;
SHOW DATABASES;
use polyphonic;

CREATE TABLE Audio(
AudioID int primary key auto_increment,
AudioName varchar(100),
AudioMetadata JSON,
AudioFile LONGBLOB,
AudioHash varchar(64) unique
);

show columns in audio;

CREATE TABLE AudioFingerprint(
FingerprintID bigint primary key auto_increment,
AudioID int,  -- have to set this as foreign key
FingerprintHash varchar(64) unique,
FingerprintOffset int,
foreign key (AudioID) references Audio (AudioID)
);

CREATE INDEX FingerprintIndex ON AudioFingerprint (FingerprintHash); -- optimization: composite indesx

CREATE TABLE Derivations(
RelationID int primary key auto_increment,
ParentID int,
ChildID int,
foreign key (ParentID) references Audio (AudioID),
foreign key (ChildID) references Audio (AudioID),
TransformationType varchar(20),
TransformationParameters JSON
);
