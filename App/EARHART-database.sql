--Entities--

create table Users (
  UID serial primary key,
  Email varchar(255) not null unique,
  psswrd varchar(255) not null,
  Username varchar(255) not null unique,
  fullname varchar(255) not null
);

create table Dataset (
  SetID serial primary key,
  Dataset_name varchar(255),
  sourcefile varchar(255),
  created_on varchar(255),
  UID int not null references Users,
  statistics varchar(255),
  identifier varchar(255)
);

create table Dataset_content (
  User_ID int,
  Item_ID int,
  Tmstmp timestamp,
  Interaction_ID serial not null,
  SetID int not null references Dataset 
  on delete cascade on update cascade,
  primary key (Interaction_ID, SetID)
);

create table Metadata (
  metadatakey serial primary key,
  Item_ID int,
  Datatype varchar(255),
  Data_meaning varchar(255),
  integ int,
  string TEXT,
  sourcefile varchar(255),
  SetID int not null references Dataset ON DELETE CASCADE
);

create table Scenario (
  Scenario_name varchar(255),
  SetID int not null,
  statistics varchar(255),
  geninfo varchar(255),  -- ToDo: VERY IMPORTANT! Add column to server
  foreign key (SetID) references Dataset ON DELETE CASCADE,
  primary key (Scenario_name, SetID)
);

create table Subset_of_Dataset(
    User_ID int,
    Item_ID int,
    Tmstmp timestamp,
    Scenario_name varchar(255),
    SetID int not null,
    gen_param varchar(255),
    foreign key(Scenario_name,SetID) references Scenario ON DELETE CASCADE,
    primary key (Scenario_name,SetID,User_ID,Item_ID)
);

create table Processing_step (
  P_ID serial,
  Code varchar(255),
  parameters varchar(255),
  Scenario_name varchar(255) not null,
  SetID int not null,
  tmstmp timestamp,
  foreign key (SetID, Scenario_name) references Scenario(SetID, Scenario_name)  ON DELETE CASCADE,
  primary key (P_ID, Scenario_name, SetID)
);

create table Model (
  Model_name varchar(255),
  Algorithm varchar(255),
  Parameters varchar(255),
  Scenario_name varchar(255) not null,
  SetID int not null,
  model_info TEXT,
  trained_time varchar(255),
  recall_cache TEXT, -- todo: update on server application!
  foreign key (Scenario_name, SetID) references Scenario(Scenario_name, SetID)  ON DELETE CASCADE,
  primary key (Model_name, Scenario_name, SetID)
);

create table Experiment (
  E_ID serial,
  Model_name varchar(255) not null,
  Scenario_name varchar(255) not null,
  SetID int not null,
  experiment_name varchar(255) not null,
  foreign key (Model_name, Scenario_name, SetID) references Model(Model_name, Scenario_name, SetID)  ON DELETE CASCADE,
  primary key (Model_name, Scenario_name, SetID, E_ID)
);

create table Experiment_user (
  E_user_ID serial,
  E_ID int not null,
  Model_name varchar(255) not null,
  Scenario_name varchar(255) not null,
  SetID int not null,
  static_user_id int,  -- Todo: IMPORTANT add to server DB
  foreign key (E_ID, Model_name, Scenario_name, SetID) references Experiment(E_ID, Model_name, Scenario_name, SetID)  ON DELETE CASCADE,
  primary key (E_user_ID, E_ID, Model_name, Scenario_name, SetID)
);

--mtm Relations--

create table Dataset_shared_with (
  SetID int references Dataset  ON DELETE CASCADE,
  UID int references Users,
  primary key (SetID, UID)
);

create table Experiment_shared_with (
  UID serial references Users,
  E_ID int,
  Model_name varchar(255),
  Scenario_name varchar(255),
  SetID int,
  foreign key (E_ID, Model_name, Scenario_name, SetID) references Experiment(E_ID, Model_name, Scenario_name, SetID)  ON DELETE CASCADE,
  primary key (UID, E_ID, Model_name, Scenario_name, SetID)
);

create table item_to_E_user (
  E_user_ID int not null,
  Item_ID int,
  unique_rel_id int,
  E_ID int not null,
  Model_name varchar(255) not null,
  Scenario_name varchar(255) not null,
  SetID int not null,
  foreign key (E_user_ID, E_ID, Model_name, Scenario_name, SetID) references Experiment_user(E_user_ID, E_ID, Model_name, Scenario_name, SetID)  ON DELETE CASCADE,
  primary key (E_user_ID, Item_ID, unique_rel_id, E_ID, Model_name, Scenario_name, SetID)
);

--Triggers--

CREATE FUNCTION total_constraint_function()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
	ASSERT NOT EXISTS (
		SELECT SetID
		FROM Dataset		
		EXCEPT 
		SELECT SetID
		FROM Dataset_content
		);
	RETURN NULL;
END;$$;

CREATE TRIGGER total_constraint_Dataset_content
AFTER UPDATE OR DELETE 
ON Dataset_content
EXECUTE PROCEDURE total_constraint_function();

CREATE CONSTRAINT TRIGGER total_constraint_Dataset
AFTER INSERT 
ON Dataset
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE PROCEDURE total_constraint_function();
