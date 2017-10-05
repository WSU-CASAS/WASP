// ar.h

#ifndef AR_H
#define AR_H

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

#define MAXSTR 80
#define MAXALENGTH 10000000
#define MAXBUFFER 256
#define DOUBLELIMIT 15

// Currently using features location, time of day, day of week,
// previous activity, and activity length
#define SENSOR 0
#define TIME 1
#define DOW 2
#define PREVIOUS 3
#define LENGTH 4

#define SENSORVALUE 3
#define LABEL 4

#define OFF 0
#define ON 1

#define MIN 0.000001
#define K 10                    // Number of folds for cross validation

#define TRUE 1
#define FALSE 0

#define NB 0
#define HMM 1
#define CRF 2

#define TRAIN 1
#define TEST 2
#define BOTH 3

#define WINDOW 10             // Test window measured in number of sensor events

typedef struct LargeNumber
{
   long double mantissa;
   long int exponent;
} LargeNumber;

char **activitynames;
char ***sensormap;
char **adatetime;
char modelfilename[MAXSTR];
int **aevents;
int **starts;
int **lengthactivities;               // The length of each activity occurrence
int **previousactivity;
int **freq;      // Frequency of actual activities and activity classifications
int *afreq;                       // The number of occurrences of each activity
int *open;                          // The start/finish status of each activity
int *stotal;                 // Total training #sensor events for each activity
int *svalues;                     // Number of possible values for each feature
int ***evidence;                   // Counts of feature values in training data
int **testevidence;                    // Counts of feature values in test data
int *numfeaturevalues;            // Number of possible values for each feature
int *selectfeatures;                        // Feature values learned from data
int **sizes;                                  // Length of activity occurrences
int **sfreq;                          // Count of sensor frequency for activity
int *partition;                                // Partition train and test data
int **thresholds;                  // Threshold values for feature value ranges
int numactivities;
int numfeatures;
int numphysicalsensors;
int numsensors;
int eval;                                        // Select items for Train/Test
int partitiontype;                                   // Deterministic or random 
int outputlevel;
int right;
int wrong;
int model;
int evnum;                             // Number of sensor events in input data
int mode;                                               // Train, test, or both
int stream;
double *prior;
double **tr;                                        // Transition probabilities
double ***emissionProb;                               // Emission probabilities
LargeNumber min;
LargeNumber *likelihood;
LargeNumber **ltr;                            // Large transition probabilities
LargeNumber *lprior;                               // Large prior probabilities
LargeNumber ***lemissionProb;                   // Large emission probabilities

void Ar();
void TrainInit();
void TestInit();
void ReadOptions(int argc, char *argv[]);
void ReadHeader(FILE *fp);
void ReadData(FILE *fp);
void CalculateState(int event[6], int size, int previous);
void CalculateEvidence(int **e);
void Finish();
void ProcessData(int activity, int occurrence, int length,
                 char *dstr, char *tstr, char *sistr, char *svstr);
void NBCTrain(int cvnum);
void NBCTest(int cvnum);
void CalculatePrior();
void SelectFeatures();
void Partition();
void MakeAllLarge();
void PrintEvent(int *event);
void PrintLargeNumber(LargeNumber num);
void Summarize();
void PrintResults();
void ReadModel();
void SaveModel();
FILE *Init(int argc, char *argv[]);
int FindActivity(char *name);
int AddActivity(char *date, char *time, char *sensorid, char *sensorvalue,
                int activity, int label, int same, int previous);
int MapSensors(char *sistr);
int cmp(int *t1, int *t2);
int comp(const void *t1, const void *t2);
int IsEqual(LargeNumber op1, LargeNumber op2);
int IsGreaterThan(LargeNumber op1, LargeNumber op2);
int DLength(int size);
double CalculateProb(double p, int a);
LargeNumber MakeLargeNumber(long double num);
LargeNumber Standardize(LargeNumber num);
LargeNumber MakeLargeNumber(long double num);
LargeNumber Add(LargeNumber op1, LargeNumber op2);
LargeNumber Subtract(LargeNumber op1, LargeNumber op2);
LargeNumber Multiply(LargeNumber op1, LargeNumber op2);
LargeNumber Divide(LargeNumber op1, LargeNumber op2);

#endif // AR_H
