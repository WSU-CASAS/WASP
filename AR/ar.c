// ar.c

// Written by Diane Cook, Washington State University, 2010
// This program reads one continuous annotated sensor data file as input.
// It trains and tests an activity recognition model using a naive Bayes
// classifier, an HMM, or a CRF.

#include "ar.h"
#include "nb.h"
#include "hmm.h"
#include "crf.h"
#include <unistd.h>
#include <sys/times.h>

// Top level function for activity recognition algorithm.
int main(int argc, char *argv[]) {
	FILE *fp;
	struct tms tmsstart, tmsend;
	clock_t startTime, endTime;
	static long clktck = 0;

	clktck = sysconf(_SC_CLK_TCK); // Determine start time of program
	startTime = times(&tmsstart);
	srand(startTime);
	printf("AR version 1.0\n\n");
	fp = Init(argc, argv); // Initialize variables and parameters
	printf("After Init()\n");
	ReadData(fp); // Read and store sensor events
        printf("After ReadData()\n");
	fclose(fp);
	if (mode != TEST)
		SelectFeatures(); // Determine ranges for feature values
	if (outputlevel > 1) // Summarize activity features
		Summarize();
	Ar(); // Activity recognition
	if (mode != TRAIN)
		PrintResults();
	Finish();

	endTime = times(&tmsend); // Report time of AR program
	//printf("AR done (elapsed CPU time = %7.2f seconds).\n",
	//		(endTime - startTime) / (double) clktck);
	return (0);
}

// Initialize parameters and data structures.
FILE *Init(int argc, char *argv[]) {
	FILE *fp;
	int i, j;

	printf("Init()\n");
	if (argc > 2) {
		fp = fopen(argv[2], "r");
		if (fp == NULL) {
			printf("Error reading parameter file %s\n", argv[2]);
			exit(1);
		}
	} else {
		printf("Reading data from standard input\n");
		fp = stdin;
	}
	model = NB; // Set default values for global variables
	strcpy(modelfilename, ".model");
	numactivities = 1;
	numfeatures = 5;
	numphysicalsensors = 1;
	numsensors = 1;
	eval = 1;
	partitiontype = 1;
	outputlevel = 1;
	evnum = 0;
	stream = 0;
	mode = BOTH;
	CRFtrainiterations = 30;
	printf("before ReadOptions()\n");
	ReadOptions(argc, argv); // Process command-line options
	printf("before ReadHeader()\n");
	ReadHeader(fp); // Process header file
	printf("before fclose()\n");
	fclose(fp);

	if (argc > 1) {
		fp = fopen(argv[1], "r");
		if (fp == NULL) {
			printf("Error reading file %s\n", argv[1]);
			exit(1);
		}
	} else {
		printf("Reading data from standard input\n");
		fp = stdin;
	}

	// Initialize variables
	aevents = (int **) malloc(MAXALENGTH * sizeof(int *));
	adatetime = (char **) malloc(MAXALENGTH * sizeof(char *));
	evidence = (int ***) malloc(numactivities * sizeof(int **));
	emissionProb = (double ***) malloc(numactivities * sizeof(double **));
	lemissionProb = (LargeNumber ***) malloc(
			numactivities * sizeof(LargeNumber **));
	freq = (int **) malloc(numactivities * sizeof(int *));
	lengthactivities = (int **) malloc(numactivities * sizeof(int *));
	previousactivity = (int **) malloc(numactivities * sizeof(int *));
	starts = (int **) malloc(numactivities * sizeof(int *));
	tr = (double **) malloc(numactivities * sizeof(double *));
	testevidence = (int **) malloc(numfeatures * sizeof(int *));
	afreq = (int *) malloc(numactivities * sizeof(int));
	open = (int *) malloc(numactivities * sizeof(int));
	stotal = (int *) malloc(numactivities * sizeof(int));
	prior = (double *) malloc(numactivities * sizeof(double));
	svalues = (int *) malloc(numfeatures * sizeof(int));
	sfreq = (int **) malloc(numactivities * sizeof(int *));
	ltr = (LargeNumber **) malloc(numactivities * sizeof(LargeNumber *));
	likelihood = (LargeNumber *) malloc(numactivities * sizeof(LargeNumber));
	lprior = (LargeNumber *) malloc(numactivities * sizeof(LargeNumber));
	thresholds = (int **) malloc(numfeatures * sizeof(int *));

	for (i = 0; i < numactivities; i++) {
		afreq[i] = 0;
		open[i] = 0;
		evidence[i] = (int **) malloc(numfeatures * sizeof(int *));
		emissionProb[i] = (double **) malloc(numfeatures * sizeof(double *));
		lemissionProb[i] = (LargeNumber **) malloc(
				numfeatures * sizeof(LargeNumber *));
		freq[i] = (int *) malloc(numactivities * sizeof(int));
		lengthactivities[i] = (int *) malloc(sizeof(int));
		previousactivity[i] = (int *) malloc(sizeof(int));
		starts[i] = (int *) malloc(sizeof(int));
		tr[i] = (double *) malloc(numactivities * sizeof(double));
		sfreq[i] = (int *) malloc(numsensors * sizeof(int));
		ltr[i] = (LargeNumber *) malloc(numactivities * sizeof(LargeNumber));
		for (j = 0; j < numfeatures; j++) {
			evidence[i][j] = (int *) malloc(numfeaturevalues[j] * sizeof(int));
			emissionProb[i][j] = (double *) malloc(
					numfeaturevalues[j] * sizeof(double));
			lemissionProb[i][j] = (LargeNumber *) malloc(
					numfeaturevalues[j] * sizeof(LargeNumber));
		}
		for (j = 0; j < numactivities; j++)
			freq[i][j] = 0;
		for (j = 0; j < numsensors; j++)
			sfreq[i][j] = 0;
	}
	for (i = 0; i < MAXALENGTH; i++)
	{
		aevents[i] = (int *) malloc(numfeatures * sizeof(int));
		adatetime[i] = (char *) malloc(26 * sizeof(char));
	}
	for (i = 0; i < numfeatures; i++) {
		testevidence[i] = (int *) malloc(numfeaturevalues[i] * sizeof(int));
		thresholds[i] = (int *) malloc((numfeaturevalues[i] - 1) * sizeof(int));
	}
	
	

	right = 0;
	wrong = 0;
	evnum = 0;
	// Because the probabilities get arbitrarily small we represent them in
	// mantissa exponent format
	min = MakeLargeNumber((long double) 1);
	min.mantissa = 1;
	min.exponent = -10000000;

	return (fp);
}

// Clean up variables.
void Finish() {
	int i, j;

	for (i = 0; i < numactivities; i++) {
		for (j = 0; j < numfeatures; j++) {
			free(evidence[i][j]);
			free(emissionProb[i][j]);
			free(lemissionProb[i][j]);
		}
		free(lengthactivities[i]);
		free(previousactivity[i]);
		free(starts[i]);
		free(evidence[i]);
		free(emissionProb[i]);
		free(lemissionProb[i]);
		free(freq[i]);
		if (sizes != NULL)
			free(sizes[i]);
		free(tr[i]);
		free(sfreq[i]);
		free(ltr[i]);
		free(activitynames[i]);
	}
	for (i = 0; i < numfeatures; i++) {
		free(testevidence[i]);
		free(thresholds[i]);
	}
	free(afreq);
	free(open);
	free(lengthactivities);
	free(previousactivity);
	free(freq);
	free(prior);
	free(lprior);
	free(stotal);
	free(svalues);
	free(selectfeatures);
	free(aevents);
	free(adatetime);
	free(starts);
	if (sizes != NULL)
		free(sizes);
	free(numfeaturevalues);
	free(tr);
	free(sfreq);
	free(ltr);
	free(evidence);
	free(testevidence);
	free(thresholds);
	free(emissionProb);
	free(lemissionProb);
	free(likelihood);
	free(activitynames);
}

// Process command-line options.
void ReadOptions(int argc, char *argv[]) {
	int i = 3;

	while (i < argc) {
		// Data should be processed in streaming fashion without segmenting
		if (strcmp(argv[i], "-stream") == 0) {
			stream = 1;
		}
		// Read in the type of evaluation method that should be used
		else if (strcmp(argv[i], "-eval") == 0) {
			i++;
			sscanf(argv[i], "%d", &eval);
			if ((eval < 1) || (eval > 4)) {
				printf("%s: eval must be 1-3\n", argv[0]);
				exit(1);
			}
			if (outputlevel > 1)
				printf("Picking data for train/test using method %d\n", eval);
		} else if (strcmp(argv[i], "-output") == 0) {
			i++;
			sscanf(argv[i], "%d", &outputlevel);
			if ((outputlevel < 1) || (outputlevel > 3)) {
				printf("%s: output must be 1-3\n", argv[0]);
				exit(1);
			}
		} else if (strcmp(argv[i], "-partitiontype") == 0) {
			i++;
			sscanf(argv[i], "%d", &partitiontype);
			if ((partitiontype < 1) || (partitiontype > 2)) {
				printf("%s: partitiontype must be 1 or 2\n", argv[0]);
				exit(1);
			}
		} else if (strcmp(argv[i], "-modelfile") == 0) {
			i++;
			sscanf(argv[i], "%s", modelfilename);
		} else if (strcmp(argv[i], "-mode") == 0) {
			i++;
			sscanf(argv[i], "%d", &mode);
			if ((mode < 1) || (mode > 3)) {
				printf("%s: mode must be 1-3\n", argv[0]);
				exit(1);
			}
		} else if (strcmp(argv[i], "-trainiterations") == 0) {
			i++;
			sscanf(argv[i], "%d", &CRFtrainiterations);
		} else {
			printf("%s: unknown option %s\n", argv[0], argv[i]);
			exit(1);
		}
		i++;
	}

	return;
}

// Set the parameter values.
void ReadHeader(FILE *fp) {
	char *cptr, buffer[MAXBUFFER], s1[80];
	int i, length;
	int readnumfeaturevalues = 0;
	printf("ReadHeader()\n");

	if (fp == NULL)
		printf("Using default parameter values\n");
	else // Process single line of parameter file
	{
		cptr = fgets(buffer, MAXBUFFER, fp);
		while (cptr != NULL) {
			//printf("cptr != NULL\n");
			length = strlen(cptr);
			if ((length > 0) && (cptr[0] != '%')) {
				sscanf(cptr, "%s", s1);

				// Read in number of activities
				if (strcmp(s1, "numactivities") == 0) {
					//printf("numactivities\n");
					cptr = fgets(buffer, MAXBUFFER, fp);
					sscanf(buffer, "%d", &numactivities);
				}
				// Read in number of features
				else if (strcmp(s1, "numfeatures") == 0) {
					//printf("numfeatures\n");
					cptr = fgets(buffer, MAXBUFFER, fp);
					sscanf(buffer, "%d", &numfeatures);
					numfeaturevalues = (int *) malloc(
							numfeatures * sizeof(int));
					selectfeatures = (int *) malloc(numfeatures * sizeof(int));
					for (i = 0; i < numfeatures; i++)
						selectfeatures[i] = 0;
				}
				// Read in number of feature values
				else if (strcmp(s1, "numfeaturevalues") == 0) {
					//printf("numfeaturevalues\n");
					for (i = 0; i < numfeatures; i++) {
						cptr = fgets(buffer, MAXBUFFER, fp);
						sscanf(buffer, "%d", &numfeaturevalues[i]);
					}
					numsensors = numfeaturevalues[SENSOR];
					readnumfeaturevalues = 1;
				}
				// Read in activity names
				else if (strcmp(s1, "activitynames") == 0) {
					//printf("activitynames\n");
					activitynames = (char **) malloc(
							numactivities * sizeof(char *));
					for (i = 0; i < numactivities; i++) {
						activitynames[i] = (char *) malloc(
								MAXSTR * sizeof(char));
						cptr = fgets(buffer, MAXBUFFER, fp);
						sscanf(buffer, "%s", activitynames[i]);
					}
				}
				// Read in which features should be automatically discretized
				else if (strcmp(s1, "selectfeatures") == 0) {
					//printf("selectfeatures\n");
					for (i = 0; i < numfeatures; i++) {
						cptr = fgets(buffer, MAXBUFFER, fp);
						sscanf(buffer, "%d", &selectfeatures[i]);
					}
				}
				// Read in the number of physical sensors used
				else if (strcmp(s1, "numphysicalsensors") == 0) {
					//printf("numphysicalsensors\n");
					cptr = fgets(buffer, MAXBUFFER, fp);
					sscanf(buffer, "%d", &numphysicalsensors);
					sensormap = (char ***) malloc(
							numphysicalsensors * sizeof(char **));
					for (i = 0; i < numphysicalsensors; i++) {
						sensormap[i] = (char **) malloc(2 * sizeof(char *));
						sensormap[i][0] = (char *) malloc(
								MAXSTR * sizeof(char));
						sensormap[i][1] = (char *) malloc(
								MAXSTR * sizeof(char));
					}
				}
				// Read in mapping of physical sensor IDs to logical sensor IDs
				else if (strcmp(s1, "mapsensors") == 0) {
					//printf("mapsensors\n");
					for (i = 0; i < numphysicalsensors; i++) {
						cptr = fgets(buffer, MAXBUFFER, fp);
						sscanf(buffer, "%s %s", sensormap[i][0],
								sensormap[i][1]);
					}
				}
				// Read in type of model to use
				else if (strcmp(s1, "model") == 0) {
					//printf("model\n");
					cptr = fgets(buffer, MAXBUFFER, fp);
					sscanf(buffer, "%s", s1);
					if (strcmp(s1, "naivebayes") == 0) {
						model = NB;
						//if (outputlevel > 0)
							//printf("Using naive bayes classifier\n");
					} else if (strcmp(s1, "hmm") == 0) {
						model = HMM;
						//if (outputlevel > 0)
						//	printf("Using hidden Markov model\n");
					} else {
						model = CRF;
						//if (outputlevel > 0)
						//	printf("Using conditional random field\n");
					}
				}
			}
			cptr = fgets(buffer, MAXBUFFER, fp); // Get next line
		}
		//printf("RANDOM PRINT!\n");
		if (readnumfeaturevalues == 0) // Use default feature values
		{
			//printf("readnumfeaturesvalues == 0\n");
			numsensors = numphysicalsensors;
			numfeaturevalues[SENSOR] = numphysicalsensors;
			numfeaturevalues[TIME] = 5;
			numfeaturevalues[DOW] = 7;
			numfeaturevalues[PREVIOUS] = numactivities;
			numfeaturevalues[LENGTH] = 3;
		}
		//printf("After if statement\n");
	}
	//printf("Leaving ReadHeader()\n");
}

// Read the sensor events from the input file, fp.  Associate the event
// with the corresponding activities.
void ReadData(FILE *fp) {
	char *cptr, buffer[256], status[80];
	char date[80], time[80], sensorid[80], sensorvalue[80], alabel[80];
	int i, sole, length, num, same, previous;

	same = 0; // New or continued activity
	sole = 0;
	previous = 0;
	cptr = fgets(buffer, 256, fp);
	while (cptr != NULL) {
		strcpy(alabel, "none");
		length = strlen(cptr);
		// Ignore lines that are empty or commented lines starting with "%"
		if ((length > 0) && (cptr[0] != '%')) {
			// Remove white space at the end of the line
			while ((length > 1)
					&& ((cptr[length - 2] == ' ') || (cptr[length - 1] == '	')))
				length--;
			// There is a label if the line ends with " begin" or " end"
			if (((cptr[length - 4] == 'e') && (cptr[length - 3] == 'n')
					&& (cptr[length - 2] == 'd'))
					|| ((cptr[length - 6] == 'b') && (cptr[length - 5] == 'e')
							&& (cptr[length - 4] == 'g')
							&& (cptr[length - 3] == 'i')
							&& (cptr[length - 2] == 'n'))) {
				sscanf(cptr, "%s %s %s %s %s %s", date, time, sensorid,
						sensorvalue, alabel, status);
				//printf("d=%s t=%s id=%s m=%s l=%s s=%s\n",date,time,sensorid,sensorvalue,alabel,status);
			} else {
				sscanf(cptr, "%s %s %s %s %s", date, time, sensorid,
						sensorvalue, alabel);
				if (strcmp(alabel, "none") != 0) // There is an activity label
					sole = 1;
			}
			//printf("d=%s t=%s id=%s m=%s l=%s s=%s\n",date,time,sensorid,sensorvalue,alabel,status);

			if (sole == 1) // A label is provided with no begin or end
					{
				num = FindActivity(alabel);
				if (open[num] == 1) // Add event to activity if open
						{
					AddActivity(date, time, sensorid, sensorvalue, num, 0, same,
							previous);
				} else // Singleton activity
				{
					AddActivity(date, time, sensorid, sensorvalue, // begin
							num, 1, same, previous);
					AddActivity(date, time, sensorid, sensorvalue, // end
							num, 1, same, previous);
					previous = num;
				}
				sole = 0;
			} else if (strcmp(alabel, "none") == 0) // No label
					{
				if (same > 0) // Continue with previous activities
						{
					for (i = 0; i < numactivities; i++) // Check for current activities
							{
						if (open[i] == 1)
							AddActivity(date, time, sensorid, sensorvalue, i, 0,
									same, previous);
					}
				}
			} else // There is an activity label for this event
			{
				num = FindActivity(alabel);
				same = AddActivity(date, time, sensorid, sensorvalue, num, 1,
						same, previous);
				if (same == 0) // Finished activity, update previous
					previous = num;
				for (i = 0; i < numactivities; i++) // Check for other current activities
						{
					if ((i != num) && (open[i] == 1))
						AddActivity(date, time, sensorid, sensorvalue, i, 0,
								same, previous);
				}
			}
		}

		cptr = fgets(buffer, 256, fp); // Get next event
	}
	for (i = 0; i < numactivities; i++) // Output warning if activity not used
		if (afreq[i] == 0)
			printf("Activity %s is not found in the data\n", activitynames[i]);
}

// Return index that corresponds to the activity label.  If the label is not
// found in the list of predefined activity labels then an error is generated
// and the program is terminated.
int FindActivity(char *name) {
	int i;

	for (i = 0; i < numactivities; i++)
		if (strcmp(name, activitynames[i]) == 0)
			return (i);

	printf("Unrecognized activity label %s\n", name);
	exit(1);
}

// Add the current sensor event to the sensor event sequence for a
// particular activity.
int AddActivity(char *date, char *time, char *sensorid, char *sensorvalue,
		int activity, int label, int same, int previous) {
	int occurrence, length;

	occurrence = afreq[activity];
	length = lengthactivities[activity][occurrence];
	if (evnum < MAXALENGTH) {
		ProcessData(activity, occurrence, length, date, time, sensorid,
				sensorvalue);
		lengthactivities[activity][occurrence] += 1;
	} else {
		printf("Event %s %s %s %s\n", date, time, sensorid, sensorvalue);
		printf("Activity length for %s exceeds maximum\n",
				activitynames[activity]);
	}

	if ((label == 1) && (open[activity] == 0)) // Starting a new activity
			{
		open[activity] = 1;
		previousactivity[activity][occurrence] = previous;
		starts[activity][occurrence] = evnum - 1;
		return (same + 1);
	} else if (label == 0) // Continue existing activity
		return (same);
	else // Finish activity
	{
		afreq[activity] += 1;
		open[activity] = 0;
		// Make room for the next activity occurrence
		starts[activity] = (int *) realloc(starts[activity],
				(afreq[activity] + 1) * sizeof(int));
		lengthactivities[activity] = (int *) realloc(lengthactivities[activity],
				(afreq[activity] + 1) * sizeof(int));
		previousactivity[activity] = (int *) realloc(previousactivity[activity],
				(afreq[activity] + 1) * sizeof(int));
		lengthactivities[activity][afreq[activity]] = 0;
		previousactivity[activity][afreq[activity]] = 0;
		starts[activity][afreq[activity]] = 0;
		return (same - 1);
	}
}

// Process and store a single sensor event.
void ProcessData(int activity, int occurrence, int length, char *dstr,
		char *tstr, char *sistr, char *svstr) {
	char temp[4];
	int dow, sensorid, sensorvalue, tnum;

	temp[0] = dstr[6]; // Compute day of week
	temp[1] = '\0';
	dow = atoi(temp);
	if (dow == 7)
		dow += 30;
	else if (dow == 8)
		dow += 61;
	temp[0] = dstr[8];
	temp[1] = dstr[9];
	temp[2] = '\0';
	dow += atoi(temp);
	dow = dow % 7;

	temp[0] = tstr[0]; // Compute time of day
	temp[1] = tstr[1];
	temp[2] = '\0';
	tnum = atoi(temp);

	sensorid = MapSensors(sistr);
	if (strcmp(svstr, "OFF") == 0)
		sensorvalue = OFF;
	else
		sensorvalue = ON;
	
	sprintf(adatetime[evnum], "%s %s", dstr, tstr);

	aevents[evnum][SENSOR] = sensorid;
	aevents[evnum][TIME] = tnum;
	aevents[evnum][DOW] = dow;
	aevents[evnum][SENSORVALUE] = sensorvalue;
	aevents[evnum][LABEL] = activity;
	evnum++;
}

// Store mapping of physical sensor IDs to logical sensor IDs.
int MapSensors(char *sistr) {
	int i;

	for (i = 0; i < numphysicalsensors; i++)
		if (strcmp(sensormap[i][0], sistr) == 0)
			return (atoi(sensormap[i][1]));

	return (0);
}

// These comparison functions are used to sort data values for equal frequency
// binning.
int cmp(int *t1, int *t2) {
	return (*t1 - *t2);
}

int comp(const void *t1, const void *t2) {
	int *v1 = (int *) t1;
	int *v2 = (int *) t2;

	return (cmp(v1, v2));
}

// Put selected feature values into ranges using user-supplied range values
// or equal-frequency binning.
void SelectFeatures() {
	int i, j, k, n, num, *data, tvalue, discretize;

	for (i = 0; i < numfeatures; i++) {
		discretize = 1;
		if (selectfeatures[i] == 0) // Ranges are hard coded
				{
			if (i == TIME) // hard code time values
					{
				for (j = 0; j < numfeaturevalues[i]; j++) {
					if (j == 0)
						thresholds[i][j] = 5; // Night / morning threshold
					else if (j == 1)
						thresholds[i][j] = 10; // Morning / mid day threshold
					else if (j == 2)
						thresholds[i][j] = 15; // Mid day / afternoon threshold
					else
						thresholds[i][j] = 20; // Afternoon / evening threshold
				}
			} else if (i == LENGTH) // hard code activity length values
					{
				for (j = 0; j < numfeaturevalues[i]; j++) {
					if (j == 0)
						thresholds[i][j] = 150; // Small / medium threshold
					else
						// Medium / large threshold
						thresholds[i][j] = 500;
				}
			} else
				discretize = 0; // Other features do not use ranges
		} else // Use equal frequency binning to select threshold values
		{
			num = 0;
			if (i == LENGTH) {
				for (j = 0; j < numactivities; j++)
					num += afreq[j];
			} else
				num = evnum;

			data = (int *) malloc(num * sizeof(int));
			n = 0;
			if (i == LENGTH) {
				for (j = 0; j < numactivities; j++)
					for (k = 0; k < afreq[j]; k++)
						data[n++] = lengthactivities[j][k];
			} else {
				for (j = 0; j < evnum; j++)
					data[n++] = aevents[j][i];
			}

			qsort(data, n, sizeof(int), comp);

			if (outputlevel > 1)
				printf("The range values for feature %d are ", i);
			for (j = 0; j < numfeaturevalues[i] - 1; j++) {
				tvalue = (j + 1) * (n / numfeaturevalues[i]);
				thresholds[i][j] = data[tvalue];
				if (outputlevel > 1)
					printf("%d ", thresholds[i][j]);
			}
			if (outputlevel > 1)
				printf("\n");
			free(data);
		}

		if (discretize == 1) {
			if (i == LENGTH) // Create array of discretized activity lengths
					{
				if (stream == 0) {
					sizes = (int **) malloc(numactivities * sizeof(int *));
					for (j = 0; j < numactivities; j++) {
						sizes[j] = (int *) malloc(afreq[j] * sizeof(int));
						for (k = 0; k < afreq[j]; k++) {
							num = 0;
							while ((num < (numfeaturevalues[i] - 1))
									&& (lengthactivities[j][k]
											> thresholds[i][num]))
								num++;
							sizes[j][k] = num;
						}
					}
				}
			} else // Reset feature to discretized values
			{
				for (j = 0; j < evnum; j++) {
					num = 0;
					while ((num < (numfeaturevalues[i] - 1))
							&& (aevents[j][i] > thresholds[i][num]))
						num++;
					aevents[j][i] = num;
				}
			}
		}
	}
}

// Use length thresholds to discretize activity length.
int DLength(int size) {
	int num;

	num = 0;
	while ((num < (numfeaturevalues[LENGTH] - 1))
			&& (size > thresholds[LENGTH][num]))
		num++;

	return (num);
}

// Summarize features of the input activities.
void Summarize() {
	int i, j, total = 0, *altotal, *astotal, time;
	float *lmean, *lvariance, *smean, *svariance;

	altotal = (int *) malloc(numactivities * sizeof(int));
	lmean = (float *) malloc(numactivities * sizeof(float));
	lvariance = (float *) malloc(numactivities * sizeof(float));
	astotal = (int *) malloc(numactivities * sizeof(int));
	smean = (float *) malloc(numactivities * sizeof(float));
	svariance = (float *) malloc(numactivities * sizeof(float));

	for (i = 0; i < numactivities; i++) {
		altotal[i] = 0;
		astotal[i] = 0;
		for (j = 0; j < afreq[i]; j++) {
			total += lengthactivities[i][j];
			altotal[i] += lengthactivities[i][j];
			time = aevents[starts[i][j]][TIME];
			astotal[i] += time;
		}
		if (afreq[i] == (float) 0) {
			lmean[i] = 0;
			smean[i] = 0;
		} else {
			lmean[i] = (float) altotal[i] / (float) afreq[i];
			smean[i] = (float) astotal[i] / (float) afreq[i];
		}
		lvariance[i] = 0;
		svariance[i] = 0;
	}

	printf("********************   Summary   ********************\n");
	printf("Total number of useful sensor events:  %d\n", total);
	for (i = 0; i < numactivities; i++) {
		printf("Activity %s has %d occurrences\n", activitynames[i], afreq[i]);
		for (j = 0; j < afreq[i]; j++) {
			printf(
					" Occurrence %d started at (%d %d %d), used %d sensor events\n",
					j, starts[i][j], aevents[starts[i][j]][SENSOR],
					aevents[starts[i][j]][TIME], lengthactivities[i][j]);
			lvariance[i] += (float) ((lengthactivities[i][j] - lmean[i])
					* (lengthactivities[i][j] - lmean[i]));
			time = aevents[starts[i][j]][TIME];
			svariance[i] += (float) ((time - smean[i]) * (time - smean[i]));
		}
		printf("\n");
		if (lmean[i] == (float) 0)
			lvariance[i] = 0;
		else
			lvariance[i] /= lmean[i];
		if (smean[i] == (float) 0)
			svariance[i] = 0;
		else
			svariance[i] /= smean[i];
		printf("activity length mean is %f, variance is %f\n", lmean[i],
				lvariance[i]);
		printf("activity start time mean is %f, variance is %f\n", smean[i],
				svariance[i]);
	}
	printf("*****************************************************\n");
}

// Learn activity models.
void Ar() {
	int i;
	printf("in Ar()\n");

	if (mode == BOTH) // Partition data into train and test cases
		Partition();
	if (mode == TRAIN) {
		TrainInit();
		if (model == NB)
			NBCTrain(-1);
		else if (model == HMM)
			HMMTrain(-1);
		else if (model == CRF)
			CRFTrain(-1);
		SaveModel();
	} else if (mode == BOTH) {
		for (i = 0; i < K; i++) // Process one fold for n-fold cross validation
				{
			TrainInit();
			if (model == NB) {
				NBCTrain(i);
				NBCTest(i);
				PrintResults();
				right = 0;
				wrong = 0;
			} else if (model == HMM) {
				HMMTrain(i);
				HMMTest(i);
			} else if (model == CRF) {
				CRFTrain(i);
				CRFTest(i);
			}
		}
	} else if (mode == TEST) {
		ReadModel();
		if (model == NB)
			NBCTest(-1);
		else if (model == HMM)
			HMMTest(-1);
		else if (model == CRF)
			CRFTest(-1);
	}
}

// Partition data streams into test and train examples.
void Partition() {
	int i, j, num = 0, count = 0;

	for (i = 0; i < numactivities; i++)
		for (j = 0; j < afreq[i]; j++)
			num++;

	partition = (int *) malloc(num * sizeof(int));

	if (partitiontype == 1) // Deterministic activity partition
			{
		for (i = 0; i < numactivities; i++)
			for (j = 0; j < afreq[i]; j++) {
				partition[count] = count % K;
				count++;
			}
	} else if (partitiontype == 2) // Random activity partition
			{
		for (i = 0; i < numactivities; i++)
			for (j = 0; j < afreq[i]; j++) {
				partition[count] = rand() % K;
				count++;
			}
	}
}

// Report the results of activity recognition.
void PrintResults() {
	int i, j, k;

/*
	if (outputlevel > 0) // Print a confusion matrix
			{
		printf("\nConfusion matrix\n");
		printf("          Class label\n   Actual");
		for (i = 0; i < numactivities; i++) {
			if (i < 10)
				printf("  %d ", i);
			else
				printf(" %d ", i);
		}
		printf("\n\n     ");
		for (i = 0; i < numactivities; i++) {
			for (j = 4; j >= 0; j--)
				if (j >= strlen(activitynames[i]))
					activitynames[i][j] = ' ';
			printf("%c%c%c%c%c ", activitynames[i][0], activitynames[i][1],
					activitynames[i][2], activitynames[i][3],
					activitynames[i][4]);
			if (strlen(activitynames[i]) < 5)
				printf(" ");
			if (strlen(activitynames[i]) < 4)
				printf(" ");
			if (strlen(activitynames[i]) < 3)
				printf(" ");
			if (strlen(activitynames[i]) < 2)
				printf(" ");
			for (j = 0; j < numactivities; j++) {
				printf("%d ", freq[i][j]);
				if (freq[i][j] < 100)
					printf(" ");
				if (freq[i][j] < 10)
					printf(" ");
			}
			if (freq[i][i] == 0)
				printf("   (%f)\n     ", (float) 0.0);
			else
				printf("   (%f)\n     ", (float) freq[i][i] / (float) afreq[i]);
		}
	}*/

	// Print accuracy results
	printf("%d  %d  %f\n", right, wrong, (float) right / (float) (right + wrong));
	//printf("right %d wrong %d Average accuracy is %f\n", right, wrong,
	//		(float) right / (float) (right + wrong));
		

	if ((outputlevel > 1) && (model == HMM)) {
		for (i = 0; i < numactivities; i++) {
			printf("\n\nactivity %s\n   emission probabilities\n",
					activitynames[i]);
			for (j = 0; j < numfeatures; j++) {
				printf("   ");
				for (k = 0; k < numfeaturevalues[j]; k++)
					PrintLargeNumber(lemissionProb[i][j][k]);
				printf("\n");
			}
			printf("\n");
			printf("   transition to ");
			for (j = 0; j < numactivities; j++) {
				printf("%s ", activitynames[j]);
				PrintLargeNumber(ltr[i][j]);
			}
		}
	}
}

// Initialize variables used to train activity model.
void TrainInit() {
	int i, j, k;

	for (i = 0; i < numfeatures; i++)
		svalues[i] = 0;

	for (i = 0; i < numactivities; i++) {
		stotal[i] = 0;
		prior[i] = (double) 0.0;

		for (j = 0; j < numsensors; j++)
			sfreq[i][j] = 0;

		for (j = 0; j < numactivities; j++)
			tr[i][j] = (double) 0.0;

		for (j = 0; j < numfeatures; j++)
			for (k = 0; k < numfeaturevalues[j]; k++)
				evidence[i][j][k] = 0;
	}
}

// Initialize variables used to test activity model.
void TestInit() {
	int i, j;

	for (i = 0; i < numfeatures; i++) {
		svalues[i] = 0;
		for (j = 0; j < numfeaturevalues[i]; j++)
			testevidence[i][j] = 0;
	}
	for (i = 0; i < numactivities; i++)
		likelihood[i] = MakeLargeNumber((long double) 1);
}

// Determine features that represent current sensor event.
void CalculateState(int *event, int size, int previous) {
	int length;

	svalues[SENSOR] = event[SENSOR];
	svalues[TIME] = event[TIME];
	svalues[DOW] = event[DOW];
	svalues[PREVIOUS] = previous;
	if (stream == 1)
		length = DLength(size);
	else
		length = size;
	svalues[LENGTH] = length;
}

// Keep track of the numbers of feature values for all activities.
void CalculateEvidence(int **e) {
	e[SENSOR][svalues[SENSOR]] += 1;
	e[TIME][svalues[TIME]] += 1;
	e[DOW][svalues[DOW]] += 1;
	e[PREVIOUS][svalues[PREVIOUS]] += 1;
	e[LENGTH][svalues[LENGTH]] += 1;
}

// Determine prior probability that a sensor event belongs to any given
// activity based on the number of sensor events that have belonged to
// each activity class in the training data.
void CalculatePrior() {
	int i, atotal;

	atotal = 0;
	// Calculate total number of sensor events in training data
	for (i = 0; i < numactivities; i++)
		atotal += stotal[i];

	// Calculate prior probability for activity as #events/#total events
	for (i = 0; i < numactivities; i++)
		prior[i] = (double) stotal[i] / (double) atotal;
}

// Compute the sum of two large numbers.
LargeNumber Add(LargeNumber op1, LargeNumber op2) {
	LargeNumber result;
	long int diff = 0;

	result.exponent = 0;
	result.mantissa = 0;

	if ((op2.exponent == 0) && (op2.mantissa == 0))
		result = op1;
	else if ((op1.exponent == 0) && (op1.mantissa == 0))
		result = op2;
	else {
		diff = abs(op1.exponent - op2.exponent);
		if (diff < DOUBLELIMIT) {
			if (op1.exponent < op2.exponent) {
				result.exponent = op1.exponent;
				result.mantissa = op2.mantissa
						* powl(10, fabs(op1.exponent - op2.exponent));
				result.mantissa += op1.mantissa;
			} else {
				result.exponent = op2.exponent;
				result.mantissa = op1.mantissa
						* powl(10, fabs(op2.exponent - op1.exponent));
				result.mantissa += op2.mantissa;
			}
		} else {
			if (op1.exponent < op2.exponent)
				result = op2;
			else
				result = op1;
		}
		result = Standardize(result);
	}

	return (result);
}

// Compute the difference of two large numbers.
LargeNumber Subtract(LargeNumber op1, LargeNumber op2) {
	op2.mantissa *= (-1.0);
	return (Add(op1, op2));
}

// Compute the product of two large numbers.
LargeNumber Multiply(LargeNumber op1, LargeNumber op2) {
	LargeNumber result;

	result.mantissa = op1.mantissa * op2.mantissa;
	result.exponent = op1.exponent + op2.exponent;
	result = Standardize(result);

	return (result);
}

// Divide two large numbers.
LargeNumber Divide(LargeNumber op1, LargeNumber op2) {
	LargeNumber result;

	result.mantissa = op1.mantissa / op2.mantissa;
	result.exponent = op1.exponent - op2.exponent;
	result = Standardize(result);

	return (result);
}

// Convert double values to mantissa exponent format for floating-point
// arithmetic.
void MakeAllLarge() {
	int i, j, k;

	for (i = 0; i < numactivities; i++) {
		if (prior[i] == (double) 0.0)
			lprior[i] = min;
		else
			lprior[i] = MakeLargeNumber((long double) prior[i]);

		for (j = 0; j < numactivities; j++) // Transition probability values
				{
			if (tr[i][j] == (double) 0.0)
				ltr[i][j] = min;
			else
				ltr[i][j] = MakeLargeNumber((long double) tr[i][j]);
		}
	}

	for (i = 0; i < numactivities; i++) // Emission probability values
			{
		for (j = 0; j < numfeatures; j++) {
			for (k = 0; k < numfeaturevalues[j]; k++) {
				if (emissionProb[i][j][k] == 0)
					lemissionProb[i][j][k] = min;
				else
					lemissionProb[i][j][k] = MakeLargeNumber(
							(long double) emissionProb[i][j][k]);
			}
		}
	}
}

// Read model parameters from a file.
void ReadModel() {
	FILE *fp;
	char name[MAXSTR];
	int i, j, k, num;

	if (model == NB)
		sprintf(name, "%s.nbc", modelfilename);
	else if (model == HMM)
		sprintf(name, "%s.hmm", modelfilename);
	else
		sprintf(name, "%s.crf", modelfilename);

	fp = fopen(name, "r");

	if (fp == NULL) {
		printf("Model file cannot be read\n");
		exit(1);
	}

	fscanf(fp, "%d\n", &numactivities);
	for (i = 0; i < numactivities; i++)
		fscanf(fp, "%s ", activitynames[i]);
	fscanf(fp, "\n");
	fscanf(fp, "%d\n", &numfeatures);
	for (i = 0; i < numfeatures; i++)
		fscanf(fp, "%d ", &numfeaturevalues[i]);
	fscanf(fp, "\n");
	for (i = 0; i < numfeatures; i++) {
		if ((i == TIME) || (i == LENGTH)) {
			for (j = 0; j < numfeaturevalues[i] - 1; j++)
				fscanf(fp, "%d ", &thresholds[i][j]);
		}
	}
	fscanf(fp, "\n");
	fscanf(fp, "%d\n", &numphysicalsensors);
	for (i = 0; i < numphysicalsensors; i++)
		fscanf(fp, "%s %s ", sensormap[i][0], sensormap[i][1]);
	fscanf(fp, "\n");
	for (i = 0; i < numactivities; i++)
		fscanf(fp, "%d ", &(stotal[i]));
	fscanf(fp, "\n");
	for (i = 0; i < numactivities; i++) {
		for (j = 0; j < numfeatures; j++)
			for (k = 0; k < numfeaturevalues[j]; k++)
				fscanf(fp, "%d	", &evidence[i][j][k]);
		fprintf(fp, "\n");
	}
	fscanf(fp, "\n");

	if (model == HMM)
		ReadHMM(fp);
	else if (model == CRF)
		ReadCRF(fp);

	for (i = 0; i < numfeatures; i++) // Discretize feature values
			{
		if (i == LENGTH) {
			if (stream == 0) {
				sizes = (int **) malloc(numactivities * sizeof(int *));
				for (j = 0; j < numactivities; j++) {
					sizes[j] = (int *) malloc(afreq[j] * sizeof(int));
					for (k = 0; k < afreq[j]; k++) {
						num = 0;
						while ((num < (numfeaturevalues[i] - 1))
								&& (lengthactivities[j][k] > thresholds[i][num]))
							num++;
						sizes[j][k] = num;
					}
				}
			}
		} else if (i == TIME) {
			for (j = 0; j < evnum; j++) {
				num = 0;
				while ((num < (numfeaturevalues[i] - 1))
						&& (aevents[j][i] > thresholds[i][num]))
					num++;
				aevents[j][i] = num;
			}
		}
	}
	fclose(fp);
}

// Save model parameters to a file.
void SaveModel() {
	FILE *fp;
	char name[MAXSTR];
	int i, j, k;

	printf("model is %d\n", model);
	if (model == NB)
		sprintf(name, "%s.nbc", modelfilename);
	else if (model == HMM)
		sprintf(name, "%s.hmm", modelfilename);
	else
		sprintf(name, "%s.crf", modelfilename);

	fp = fopen(name, "w");

	if (fp == NULL) {
		printf("Model file cannot be created\n");
		exit(1);
	}

	fprintf(fp, "%d\n", numactivities);
	for (i = 0; i < numactivities; i++)
		fprintf(fp, "%s ", activitynames[i]);
	fprintf(fp, "\n");
	fprintf(fp, "%d\n", numfeatures);
	for (i = 0; i < numfeatures; i++)
		fprintf(fp, "%d ", numfeaturevalues[i]);
	fprintf(fp, "\n");
	for (i = 0; i < numfeatures; i++) {
		if ((i == TIME) || (i == LENGTH)) {
			for (j = 0; j < numfeaturevalues[i] - 1; j++)
				fprintf(fp, "%d ", thresholds[i][j]);
		}
	}
	fprintf(fp, "\n");
	fprintf(fp, "%d\n", numphysicalsensors);
	for (i = 0; i < numphysicalsensors; i++)
		fprintf(fp, "%s %s ", sensormap[i][0], sensormap[i][1]);
	fprintf(fp, "\n");
	for (i = 0; i < numactivities; i++)
		fprintf(fp, "%d ", stotal[i]);
	fprintf(fp, "\n");
	for (i = 0; i < numactivities; i++) {
		for (j = 0; j < numfeatures; j++)
			for (k = 0; k < numfeaturevalues[j]; k++)
				fprintf(fp, "%d	", evidence[i][j][k]);
		fprintf(fp, "\n");
	}

	if (model == HMM)
		SaveHMM(fp);
	else if (model == CRF)
		SaveCRF(fp);

	fclose(fp);
}

// Convert double to mantissa exponent number representation.
LargeNumber MakeLargeNumber(long double num) {
	LargeNumber result;

	result.exponent = 0;
	result.mantissa = num;
	result = Standardize(result);

	return (result);
}

// Convert large number to mantissa exponent format for floating-point
// arithmetic.
LargeNumber Standardize(LargeNumber num) {
	long double sign = 1.0;
	LargeNumber result = num;

	if (result.mantissa != 0) {
		if (result.mantissa < 0) {
			result.mantissa = (long double) fabs(result.mantissa);
			sign = -1.0;
		}
		while (result.mantissa >= 10) {
			result.mantissa /= 10;
			result.exponent += 1;
		}
		while (result.mantissa < 1) {
			result.mantissa *= 10;
			result.exponent -= 1;
		}

		result.mantissa = sign * result.mantissa;
	} else
		result.exponent = 0;

	return result;
}

// Test the equality of two large numbers.
int IsEqual(LargeNumber op1, LargeNumber op2) {
	if ((op1.exponent == op2.exponent) && (op1.mantissa == op2.mantissa))
		return (TRUE);
	else
		return (FALSE);
}

// Determine if large number op1 is greater than large number op2.
int IsGreaterThan(LargeNumber op1, LargeNumber op2) {
	LargeNumber temp;

	// Handle case where one number is negative and the other is not
	if ((op1.mantissa < 0) && (op2.mantissa >= 0))
		return (FALSE);
	if ((op1.mantissa >= 0) && (op2.mantissa < 0))
		return (TRUE);

	// If both negative, then make positive and swap
	if ((op1.mantissa < 0) && (op2.mantissa < 0)) {
		temp.exponent = op1.exponent;
		temp.mantissa = (-1.0 * op1.mantissa);
		op1.exponent = op2.exponent;
		op1.mantissa = (-1.0 * op2.mantissa);
		op2 = temp;
	}

	if (op1.exponent > op2.exponent) {
		return (TRUE);
	} else if (op1.exponent == op2.exponent) {
		if (op1.mantissa > op2.mantissa) {
			return (TRUE);
		}
	}

	return (FALSE);
}

// Print the description of a sensor event.
void PrintEvent(int *event) {
	printf("%d ", event[SENSOR]);
	printf("%d ", event[TIME]);
	printf("%d ", event[DOW]);
	printf("%d ", event[SENSORVALUE]);
	printf("%d ", event[LABEL]);
}

// Print a large number in mantissa exponent format.
void PrintLargeNumber(LargeNumber new)
{
	printf(" %fe%d ", (float) new.mantissa, (int) new.exponent);
}
