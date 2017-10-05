// crf.h

#ifndef CRF_H
#define CRF_H

// Written by Larry Holder and Diane Cook, Washington State University, 2010.

// Attributes that accompany the activity label on an event can be
// treated as ordered (value = 1), in which case the CRF features
// include the attribute's position and value. Or, the attributes can
// be treated as a bag-of-attribute values with no order (value = 0),
// in which case the CRF features just contain the attribute's value.
#define CRF_ORDERED_ATTRIBUTES 1

// CRF can predict the activity of each event or the activity of an
// entire event sequence. The following define controls this choice.
// A value of 1 means that CRF predicts an activity for each event,
// 0 means CRF predicts one activity label for each event sequence
// based on the most frequent activity predicted for individual events
// in the sequence.
#define CRF_PREDICT_EVENT 1

#define CRF_NO_CV 1 // CRF_NO_CV=1 (true) means train/test on all data
                    // otherwise, use cross-validation as usual
		    // The number of folds is defined by K

// Within one iteration, optimizer will try this number of times to correct
// the weight vector to perform gradient descent (get it to be more optimal).
// This is recommended to be a number between 5 and 7.
#define CRF_NUM_LBFGS_CORRECTIONS 7

// These two control smoothing.  Lower values mean more smoothing is needed
// (more noise in the data, smaller jumps in gradient descent).
#define CRF_LOGLI_CONSTANT 0.0
#define CRF_LOGLI_SIGMA_SQR 100.0

#define CRF_STATE_FEATURE 0
#define CRF_TRANSITION_FEATURE 1
#define CRF_MIN_FEATURE_FREQ 2
#define CRF_INITIAL_FEATURE_WEIGHT 0.0

// CRF features
//   State features s(y,x,i)
//   Transition features t(y,yp,x,i)
// where a feature is a function of the entire input sequence x, the
// current position i in x, the label yp at i, and the label y at i-1.
typedef struct {
   int type;  // CRF_STATE_FEATURE or CRF_TRANSITION_FEATURE
   int pos;   // Position of state feature in input event feature tuple
   int val;   // Value of pos-th state feature in input event
   int yp;    // Event label at current position (y')
   int y;     // Event label at previous position (y); for transition features
   int freq;  // Frequency of occurrence of this feature
   double weight; // Feature weight (to be learned)
} CRFFeature;

typedef struct {
   LargeNumber prob; // Probability of transition to next label
   int label;        // Previous label that max-prob transition came from
} CRFViterbiProb;

// Global CRF variables
int numCRFFeatures;
int sizeCRFFeatures;
CRFFeature *CRFFeatures;
LargeNumber *CRF_Fyx;    // Global feature vector Fyx for a sequence
LargeNumber *CRF_ExpFyx; // Expected value of the feature vector for a sequence
LargeNumber **CRF_alpha; // Forward state-cost vectors
LargeNumber **CRF_beta;  // Backward state-cost vectors
LargeNumber ***CRF_M;    // Label x label matrix M[i][y][yp] over sequence
CRFViterbiProb **CRFViterbiProbs; // Results of Viterbi on a test sequence
int *CRFTestSeqLabels;   // Holds predicted labels for a test sequence
                         // Used for generating label for a window of events
// The number of training iterations.  More iterations tends to produce better
// results but takes more time to run. If no improvement then training
// will stop early.
int CRFtrainiterations;

void CRFGenerateFeatures(int);
void AddStateFeature(int, int, int);
void AddTransitionFeature(int, int);
void RemoveRareCRFFeatures();
void PrintCRFFeature(FILE *, int);
void CRFTrain(int);
void ComputeLogLikelihoodAndGradient(int, double*, double*, double*);
void CRFTest(int);
void ComputeCRF_M(int, int, int);
void CRFViterbi(int);
void CRFEvaluateByEvent(int, int);
void CRFEvaluateByEventSeq (int, int);
void VectorMatrixMult(int, LargeNumber*, LargeNumber**, LargeNumber*);
void MatrixVectorTransposeMult(int, LargeNumber**, LargeNumber*, LargeNumber*);
void OutputSimpleData(FILE *);
void SaveCRF(FILE *fp);
void ReadCRF(FILE *fp);
int GetStateFeatureIndex(int, int, int);
int GetTransitionFeatureIndex(int, int);
double EvaluateCRFFeature(int, int, int, int, int);
double CRFNorm(int, double*);

#endif // CRF_H
