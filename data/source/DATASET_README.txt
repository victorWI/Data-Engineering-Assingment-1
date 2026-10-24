This readme file was generated on January 13, 2023 by William D. Ristenpart

GENERAL INFORMATION

Title of Dataset: Consumer Preference Data for Black Coffee

Author/Principal Investigator Information
Name: William D. Ristenpart
ORCID: 0000-0002-4935-6310
Institution: University of California Davis
Address: 1 Shields Ave., Davis, CA 95616 USA
Email: wdristenpart@ucdavis.edu

Author/Associate or Co-investigator Information
Name: Jean-Xavier Guinard
ORCID: 0000-0001-6386-3055
Institution: University of California Davis
Address: 1 Shields Ave., Davis, CA 95616 USA
Email: jxguinard@ucdavis.edu

Date of data collection: April to June 2019
Geographic location of data collection: Davis, CA
Information about funding sources that supported the collection of the data: Coffee Science Foundation


SHARING/ACCESS INFORMATION

Licenses/restrictions placed on the data: This data is licensed under a CC0 1.0 Universal (CC0 1.0) Public Domain Dedication license.

Links to publications that cite or use the data: 
   Cotter et al., Journal of Food Science, 2021, https://doi.org/10.1111/1750-3841.15561
   Ristenpart et al., Scientific Reports, 2022, https://doi.org/10.1038/s41598-022-23904-4
Links to other publicly accessible locations of the data: n/a
Links/relationships to ancillary data sets: n/a
Was data derived from another source?  no
Recommended citation for this dataset: Cotter, Ristenpart, & Guinard (2022) “Consumer preference data for black coffee,” Dryad Digital Depository, https://doi.org/10.25338/B8993H.
DATA & FILE OVERVIEW
File List:  cotter_dataset.csv
Are there multiple versions of the dataset?  No

METHODOLOGICAL INFORMATION
Description of methods used for collection/generation of data: please see cited links above (Cotter et al. and Ristenpart et al.)
Methods for processing the data: Almost all data in this dataset are either identifiers (e.g., which judge or which target brew condition) or raw data (e.g., temperature, pH, or consumer preference scores).  The only interpreted data was the percent extraction, calculated as described in the above references from the measured total dissolved solids and brew mass. The other interpreted data is the “Cluster,” which denotes whether an individual consumer was classified into one of two consumer preference segments, as described in detail in Cotter et al. 2021. 
Instrument- or software-specific information needed to interpret the data: The “Setting” column refers to the specific programmatic code used in the commercial coffee brewers, Curtis G4TP1S63A3100 ThermoPro Single 1 Gallon Coffee Brewers.  The “Grind” column refers to the grind size setting on Mahlkönig Guatemala Lab Grinder.
Environmental/experimental conditions: all data were acquired in the Sensory Building at the Robert Mondavi Institute for Wine and Food Science at UC Davis.
Describe any quality-assurance procedures performed on the data: All transcribed data was doublechecked manually after entry into the spreadsheet.
People involved with sample collection, processing, analysis and/or submission: Andrew Cotter generated the dataset; William Ristenpart prepared it for submission to the data depository.
DATA-SPECIFIC INFORMATION FOR: cotter_dataset.csv
Number of variables: 48
Number of cases/rows: 3186.    (A total of 118 individuals each tasted 27 distinct coffees.)
Variable List: 
   Judge:  numerical identifier of an individual person.  Ranges from 1 to 118.
   Cluster: numerical identifier for which consumer preference segmentation cluster the individual judge was identified as belonging to.  Either 1 or 2.  (See Cotter et al. 2021).
   Week: identifies which week the tasting of that coffee occurred. Either 1, 2, or 3 for first, second, or third weeks respectively.
   Session Number: identifies which of the 18 unique tasting sessions this tasting occurred at.  Ranges from 1 to 18 (with six tastings per week over three weeks).
   Position: identifies the order in which this specific coffee was sampled within a session.  Range from 1 to 10 (for first to last coffees sampled).
   Brew: denotes the target brew conditions.  The first number identifies the target brew temperature, the second number identified the target total dissolved solids (TDS), and the third number identifies the target percent extraction (PE).  For example, 87-1.0-16 denotes 87 degrees Celsius, 1% TDS, and 16% PE.
   Temp.x: identifies whether the target brew temperature was “low”, “medium”, or “high,” referring to 87, 90, or 93 degrees Celsius, respectively.
   TDS.x: identifies whether the target total dissolved solids was “low”, “medium”, or “high,” referring to 1%, 1.25%, or 1.5%, respectively.
   PE.x: identifies whether the target percent extraction was “low”, “medium”, or “high,” referring to 16%, 20%, or 24%, respectively.
   Dose: the mass, in grams, of coffee grounds added to the brewer.
   Setting: the equipment-specific programming code used to brew the coffee in the Curtis brewer.
   Grind: the equipment-specific setting used to grind the coffee in the Mahlkönig grinder.
   Empty Carafe: the mass, in grams, of the empty carafe.
   Full Carafe: the mass, in grams, of the full carafe after brewing.
   Brew Mass: the mass, in grams, of the brewed coffee.
   TDS_1: the total dissolved solids, expressed as a percentage, of the brewed coffee as measured with a digital refractometer.
   Percent Extraction: the percent extraction from the coffee grounds, expressed as a percentage, as calculated using the TDS and the brew mass (cf. Cotter et al. 2021).
   pH: the pH of the brewed coffee.
   Initial NaOH: the volume, in milliliters, of 0.1 molar NaOH prior to adding to 50 mL of brewed coffee to determine the titratable acidity.
   Final NaOH: the volume, in milliliters, of 0.1 molar NaOH after adding to 50 mL of brewed coffee to determine the titratable acidity.  The difference between initial and final represents that volume added.
   Titration pH: the final pH of the solution after adding the NaOH.
   Volume: the actual volume, in milliliters, of 0.1 molar NaOH added to titrate 50 mL of brewed coffee to a target pH of 8.2.
   Brew Temperature: the temperature, in degrees Celsius, of the brew in the carafe after completion of the brewing cycle.
   Pour Temperature: the temperature, in degrees Celsius, of the brew in the paper cup immediately after pouring.
   90Sec Temperature: the temperature, in degrees Celsius, of the brew in the paper cup after a 90-second wait to allow cooling.
   Liking: the consumer assessment of hedonic liking, on the classic 9-point scale with values ranging from 1 to 9.
   Temp: the consumer assessment of the adequacy of the beverage temperature, using the just-about-right (JAR) scale, where 1 denotes “much too cold”, 2 denotes “somewhat too cold”, 3 denotes “just-about-right”, 4 denotes “somewhat too hot”, and 5 denotes “much too hot.”
   Flavor Intensity: the consumer assessment of the adequacy of the overall flavor intensity, using the just-about-right (JAR) scale, where 1 denotes “too little”, 2 denotes “somewhat too little”, 3 denotes “just-about-right”, 4 denotes “somewhat too much”, and 5 denotes “too much.”
   Acidity: the consumer assessment of the adequacy of the overall acidity, using the just-about-right (JAR) scale, where 1 denotes “too little”, 2 denotes “somewhat too little”, 3 denotes “just-about-right”, 4 denotes “somewhat too much”, and 5 denotes “too much.”
   Mouthfeel: the consumer assessment of the adequacy of the overall mouthfeel, using the just-about-right (JAR) scale, where 1 denotes “much too thin”, 2 denotes “somewhat too thin”, 3 denotes “just-about-right”, 4 denotes “somewhat too thick”, and 5 denotes “much too thick.”
  Tea.floral, Fruit, Citrus, Green.veg, Paper.wood, Burnt, Cereal, Nutty, Dark.chocolate, Caramel, Bitter, Astringent, Roasted, Sour, Thick.viscous, Sweet, & Rubber: binary values indicating whether or not the consumer detected the respective sensory attribute in the coffee, where 0 denotes “not detected” and 1 denotes “detected.” 
   Purchase.intent: the consumer assessment of whether they would purchase this coffee at a $3 price point, using a 5-point bipolar scale where 1 is very unlikely and 5 is very likely.
Missing data codes: Some titration pH values were inadvertently not recorded. These missing values are denoted by “n/a”.  In all cases the missing values were close to pH 8.2.

