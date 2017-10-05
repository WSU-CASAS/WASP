// crf.c
//
// Written by Larry Holder and Diane Cook, Washington State University, 2010.
//
// Conditional random field code, based on Sha and Pereira's 2003
// technical report "Shallow Parsing with Conditional Random Fields".
//
// Also consulted Lafferty et al.'s 2001 ICML paper "Conditional
// Random Fields: Probabilistic Models for Segmenting and Labeling
// Sequence Data".
//
// Also consulted and compared against Phan et al.'s FlexCRFs system
// available at http://flexcrfs.sourceforge.net.

#include <errno.h>
#include "ar.h"
#include "crf.h"
#include "lbfgs.h"

// CRFGenerateFeatures
//   cvnum = test partition/fold; don't generate features from this partition
//
//   If CRF_ORDERED_ATTRIBUTES = 1 (true):
//
//   Each event in the input sequence is assumed to be a (numfeatures-1)-sized
//   tuple of integer-valued features followed by the label. For each unique
//   observed combination of feature/feature-value/label, we create a Boolean
//   CRF state feature. For each unique combination of observed label pairs,
//   we create a CRF transition feature. For example, assume the following two
//   consecutive events:
//      1 2 3 4 5
//      1 3 2 4 5
//   The first event would generate the state features s_0_1_5, s_1_2_5,
//   s_2_3_5 and s_3_4_5, where the meaning is
//   s_<position_in_event>_<value>_<label>. The second event would generate
//   the additional (unique) state features s_1_3_5 and s_2_2_5. Finally, we
//   generate the transition feature between the two events t_5_5, where the
//   meaning is t_<label at (i-1)>_<label at i>.
//
//   If CRF_ORDERED_ATTRIBUTES = 0 (false):
//
//   CRF transition features are the same as above, but the state
//   features are of the form s_<value>_<label>, that is the attributes
//   of an event are considered unordered (i.e., bag of values).
//   Most NLP uses of CRF treat attributes as a bag of words, but for
//   activity recognition ordering is useful.
void CRFGenerateFeatures(int cvnum)
{
   int a, aIdx, i, f, n, seqNum = 0, start, snum, prev;

   sizeCRFFeatures = 10;
   numCRFFeatures = 0;
   CRFFeatures = (CRFFeature *) malloc(sizeCRFFeatures * sizeof(CRFFeature));

   // Process training sequences
   for (a=0; a<numactivities; a++)
   {
      for (aIdx=0; aIdx<afreq[a]; aIdx++)
      {
         if (CRF_NO_CV || (partition[seqNum] != cvnum))
         {
            start = starts[a][aIdx];
            snum = lengthactivities[a][aIdx];
	    prev = start;
            for (i=0, n=0; n<snum; i++)
            {
	      // Only consider events that are part of this activity,
	      // ignore events for overlapping activities
	      if (1) /* (a == aevents[start+i][LABEL]) */
	      {
                 // Process ith event of aIdx occurrence of activity label a
                 // aevents[start+i]
                 if (i > 0)
                    AddTransitionFeature(aevents[start+i][numfeatures-1],
                                         aevents[prev][numfeatures-1]);
                  for (f=0; f<(numfeatures-1); f++)
                  {
                     if (CRF_ORDERED_ATTRIBUTES == 0)   // not ordered, pos is 0
                        AddStateFeature(0, aevents[start+i][f],
                                        aevents[start+i][numfeatures-1]);
		                                        // else ordered, pos = f
                     else AddStateFeature(f, aevents[start+i][f],
		                          aevents[start+i][numfeatures-1]);
	          }
		  prev = start+i;
	          n++;
               }
            }
         }
         seqNum++;
      }
   }
   RemoveRareCRFFeatures();
}


// Add a unique state feature if found in the data
void AddStateFeature(int position, int value, int label)
{
   int index;
  
   index = GetStateFeatureIndex(position, value, label);
   if (index < 0)                                                 // new feature
   {
      if (sizeCRFFeatures == numCRFFeatures) // Add more memory
      {
         sizeCRFFeatures = 2 * sizeCRFFeatures;
         CRFFeatures = (CRFFeature *)
                         realloc(CRFFeatures,
                                 sizeCRFFeatures * sizeof(CRFFeature));
      }
      CRFFeatures[numCRFFeatures].type = CRF_STATE_FEATURE;
      CRFFeatures[numCRFFeatures].pos = position;
      CRFFeatures[numCRFFeatures].val = value;
      CRFFeatures[numCRFFeatures].yp = label;
      CRFFeatures[numCRFFeatures].y = -1; // not used by state feature
      CRFFeatures[numCRFFeatures].freq = 1;
      CRFFeatures[numCRFFeatures].weight = CRF_INITIAL_FEATURE_WEIGHT;
      numCRFFeatures++;
   }
   else                           // feature already exists; increment frequency
      CRFFeatures[index].freq++;
}


// Return index for existing state feature
int GetStateFeatureIndex(int position, int value, int label)
{
   int i;

   for (i=0; i<numCRFFeatures; i++)
      if ((CRFFeatures[i].type == CRF_STATE_FEATURE) &&
          (CRFFeatures[i].pos == position) &&
          (CRFFeatures[i].val == value) &&
          (CRFFeatures[i].yp == label))
         return i;
   return -1;
}


// Add unique transition feature if found in the data
void AddTransitionFeature(int currLabel, int prevLabel)
{
   int index;
   
   index = GetTransitionFeatureIndex (currLabel, prevLabel);
   if (index < 0)                                                 // new feature
   {
      if (sizeCRFFeatures == numCRFFeatures) // Add more memory
      {
         sizeCRFFeatures = 2 * sizeCRFFeatures;
         CRFFeatures = (CRFFeature *)
                          realloc (CRFFeatures,
                                   sizeCRFFeatures * sizeof(CRFFeature));
      }
      CRFFeatures[numCRFFeatures].type = CRF_TRANSITION_FEATURE;
      CRFFeatures[numCRFFeatures].pos = -1; // not used by transition feature
      CRFFeatures[numCRFFeatures].val = -1; // not used by transition feature
      CRFFeatures[numCRFFeatures].yp = currLabel;
      CRFFeatures[numCRFFeatures].y = prevLabel;
      CRFFeatures[numCRFFeatures].freq = 1;
      CRFFeatures[numCRFFeatures].weight = CRF_INITIAL_FEATURE_WEIGHT;
      numCRFFeatures++;
   }
   else                           // feature already exists; increment frequency
   {
      CRFFeatures[index].freq++;
   }
}


// Return index for existing transition feature
int GetTransitionFeatureIndex(int currLabel, int prevLabel)
{
   int i;

   for (i=0; i<numCRFFeatures; i++)
      if ((CRFFeatures[i].type == CRF_TRANSITION_FEATURE) &&
          (CRFFeatures[i].yp == currLabel) &&
          (CRFFeatures[i].y == prevLabel))
         return i;
   return -1;
}


// Remove features that do not appear with enough frequency in the input data
void RemoveRareCRFFeatures()
{
   int i, numFreqFeatures = 0, numNewCRFFeatures = 0;
   CRFFeature *newCRFFeatures;

   // Count number of non-rare features
   for (i=0; i<numCRFFeatures; i++)
      if (CRFFeatures[i].freq >= CRF_MIN_FEATURE_FREQ)
         numFreqFeatures++;

   // Allocate new CRFFeatures list
   newCRFFeatures =
      (CRFFeature *) malloc(numFreqFeatures * sizeof(CRFFeature));

   // Copy over non-rare features
   for (i=0; i<numCRFFeatures; i++)
      if (CRFFeatures[i].freq >= CRF_MIN_FEATURE_FREQ)
      {
         newCRFFeatures[numNewCRFFeatures].type = CRFFeatures[i].type;
         newCRFFeatures[numNewCRFFeatures].pos = CRFFeatures[i].pos;
         newCRFFeatures[numNewCRFFeatures].val = CRFFeatures[i].val;
         newCRFFeatures[numNewCRFFeatures].yp = CRFFeatures[i].yp;
         newCRFFeatures[numNewCRFFeatures].y = CRFFeatures[i].y;
         newCRFFeatures[numNewCRFFeatures].freq = CRFFeatures[i].freq;
         newCRFFeatures[numNewCRFFeatures].weight = CRFFeatures[i].weight;
         numNewCRFFeatures++;
      }
   numCRFFeatures = numNewCRFFeatures;
   sizeCRFFeatures = numNewCRFFeatures;
   free(CRFFeatures);
   CRFFeatures = newCRFFeatures;
}


// Evaluate CRF feature at aeventOffset position of sequence starting at
// aevents[aeventStart]. The current (yp) and previous (y) output labels
// are provided as inputs. For training, they will come from aevents[].
// For testing, they will be provided based on the labels being tried
// by the Viterbi algorithm.
double EvaluateCRFFeature(int featureIndex, int aeventStart,
                          int aeventOffset, int y, int yp)
{
   int f;
   double value = 0.0;

   if (CRFFeatures[featureIndex].type == CRF_STATE_FEATURE)
   {
      if (CRF_ORDERED_ATTRIBUTES == 0)                            // not ordered
      {
         for (f=0; f<(numfeatures-1); f++)
            if ((CRFFeatures[featureIndex].val ==
                 aevents[aeventStart+aeventOffset][f]) &&
                (CRFFeatures[featureIndex].yp == yp))
               value += 1.0;
      }
      else
      {
         if ((CRFFeatures[featureIndex].val ==
              aevents[aeventStart+aeventOffset][CRFFeatures[featureIndex].pos])
	      && (CRFFeatures[featureIndex].yp == yp))
            value = 1.0;
      }
   }
   else                                                // CRF_TRANSITION_FEATURE
   {
      if ((CRFFeatures[featureIndex].yp == yp) &&
          (CRFFeatures[featureIndex].y == y))
         value = 1.0;
   }
   return value;
}


// Print details of a CRF feature
void PrintCRFFeature(FILE *fp, int i)
{
   if (CRFFeatures[i].type == CRF_STATE_FEATURE)
   {
      if (CRF_ORDERED_ATTRIBUTES == 0)                            // not ordered
      {
          fprintf(fp, "s_%d_%d (%f) [%d]\n",
                   CRFFeatures[i].yp, CRFFeatures[i].val,
                   CRFFeatures[i].weight, CRFFeatures[i].freq);
      }
      else
      {
          fprintf(fp, "s_%d_%d_%d (%f) [%d]\n",
                   CRFFeatures[i].pos, CRFFeatures[i].val, CRFFeatures[i].yp,
                   CRFFeatures[i].weight, CRFFeatures[i].freq);
      }
   }
   else
   {
      fprintf(fp, "t_%d_%d (%f) [%d]\n",
               CRFFeatures[i].yp, CRFFeatures[i].y, CRFFeatures[i].weight,
               CRFFeatures[i].freq);
   }
}


// CRFTrain
// cvnum = test partition/fold; don't train using this partition
void CRFTrain(int cvnum)
{
   int i, y, a, aIdx, seqNum, maxSeqLen, iterations=0;

   if (mode == TRAIN)
      printf("CRF Train\n");
   else printf("CRF Train (CV fold %d of %d) ...\n\n", (cvnum+1), K);

   // Generate features
   CRFGenerateFeatures(cvnum);

   if (outputlevel > 1)
   {
      for (i=0; i<numCRFFeatures; i++)
      {
         printf("Feature %d: ", i);
         PrintCRFFeature(stdout, i);
      }
      printf("\n");
   }

   // Find maximum sequence length
   seqNum = 0;
   maxSeqLen = 0;
   for (a=0; a<numactivities; a++)
      for (aIdx=0; aIdx<afreq[a]; aIdx++)
      {
         if (CRF_NO_CV || (partition[seqNum] != cvnum))
            if (lengthactivities[a][aIdx] > maxSeqLen)
               maxSeqLen = lengthactivities[a][aIdx];
         seqNum++;
      }

   // Print out some stats
   if (outputlevel > 1)
   {
      printf("Number of activities = %d\n", numactivities);
      printf("Number of sequences = %d\n", seqNum);
      printf("Maximum sequence length = %d\n", maxSeqLen);
      printf("Number of features = %d\n", numCRFFeatures);
      printf("\n");
   }

   // Initialize global variables
   CRF_Fyx = (LargeNumber *) malloc(numCRFFeatures * sizeof(LargeNumber));
   CRF_ExpFyx = (LargeNumber *) malloc(numCRFFeatures * sizeof(LargeNumber));
   CRF_alpha = (LargeNumber **) malloc(maxSeqLen * sizeof(LargeNumber *));
   CRF_beta = (LargeNumber **) malloc(maxSeqLen * sizeof(LargeNumber *));
   CRF_M = (LargeNumber ***) malloc(maxSeqLen * sizeof(LargeNumber **));
   for (i=0; i<maxSeqLen; i++)
   {
      CRF_alpha[i] =
         (LargeNumber *) malloc(numactivities * sizeof(LargeNumber));
      CRF_beta[i] = (LargeNumber *) malloc(numactivities * sizeof(LargeNumber));
      CRF_M[i] = (LargeNumber **) malloc(numactivities * sizeof(LargeNumber *));

      // This is a labelxlabel matrix.  For every possible transition from
      // one event (with a label) to another there is an entry in the matrix.
      // There is a separate matrix for each event in the sequence.
      for (y=0; y<numactivities; y++)
         CRF_M[i][y] =
	    (LargeNumber *) malloc(numactivities * sizeof(LargeNumber));
   }

   // Parameters to LBFGS gradient descent optimizer
   long int n = numCRFFeatures;
   long int m = CRF_NUM_LBFGS_CORRECTIONS;
   double lambda[n]; // Solution vector (feature weights)
   double logLi; // Function value (log likelihood at lambda)
   double logLiGrad[n]; // Function gradient (gradient of logLi at lambda)
   long int diagco = 0; // No diagonal provided as input (0=false)
   double diag[n]; // Diagonal of H matrix (passed in, but not used)
   long int iprint[2] = {-1,0}; // Controls amount/type of output
   double eps = 1e-4; // Solution accuracy
   double xtol = 1e-16; // Estimate of machine precision
   double workspace[n*(2*m+1)+(2*m)]; // Workspace for LBFGS
   long int iflag = 0; // Flag indicating result of call to LBFGS

   // Initialize feature weights
   for (i=0; i<n; i++)
      lambda[i] = CRFFeatures[i].weight;

   // Optimize feature weights
   do
   {
      if (outputlevel > 1)
      {
         for (i=0; i<numCRFFeatures; i++)
         {
            printf("  lambda[%d] = %f, \t", i, lambda[i]);
            PrintCRFFeature(stdout, i);
         }
         printf("\n");
      }

      printf("CRF Iteration %d of %d:\n\n", (iterations+1), CRFtrainiterations);

      // This computes the value of a function and the gradient of a function
      // at the point lambda.  The function is logLi and the gradient of the
      // function is logLiGrad.
      ComputeLogLikelihoodAndGradient(cvnum, lambda, &logLi, logLiGrad);

      // Print out the value of the function and the gradient for
      // the point lambda. Gradient descent tries to get the gradient
      // to be close to 0.
      if (outputlevel > 1)
      {
         printf("  Log-likelihood = %f\n", logLi);
         printf("  Norm(Log-likelihood gradient) = %f\n",
                CRFNorm(numCRFFeatures, logLiGrad));
      }
      if (outputlevel > 1)
         printf("  Norm(lambda) = %f\n\n", CRFNorm(numCRFFeatures, lambda));

      if (outputlevel > 1)
      {
         for (i=0; i<numCRFFeatures; i++)
         {
             printf("  logLiGrad[%d] = %f, \t", i, logLiGrad[i]);
             PrintCRFFeature(stdout, i);
         }
         printf("\n");
      }

     // Negate logLi and LogLiGrad, because LBFGS minimizes and we want to
     // maximize
     logLi *= -1.0;
     for (i=0; i<n; i++)
        logLiGrad[i] *= -1.0;

     // This is the gradient descent step, modify lambda to be closer
     // to the maximum probability value.
     lbfgs(&n, &m, lambda, &logLi, logLiGrad, &diagco, diag, iprint,
           &eps, &xtol, workspace, &iflag);
     iterations++;
   } while ((iflag > 0) && (iterations < CRFtrainiterations));
   if (iflag < 0)
      printf("LBFGS: error (iflag = %ld)\n\n", iflag);

   // Update global feature weights to learn from gradient descent step
   for (i=0; i<n; i++)
      CRFFeatures[i].weight = lambda[i];

   if (outputlevel > 1)                                    // Print out features
   {
      printf("Number of features = %d\n", numCRFFeatures);
      for (i=0; i<numCRFFeatures; i++)
         PrintCRFFeature (stdout, i);
   }

   // Free global memory
   free(CRF_Fyx);
   free(CRF_ExpFyx);

   for (i=0; i<maxSeqLen; i++)
   {
      free(CRF_alpha[i]);
      free(CRF_beta[i]);
      for (y=0; y<numactivities; y++)
         free(CRF_M[i][y]);
      free(CRF_M[i]);
   }

   free(CRF_alpha);
   free(CRF_beta);
   free(CRF_M);
}


// Compute current gradient
void ComputeLogLikelihoodAndGradient(int cvnum, double lambda[],
                                     double *logLi, double logLiGrad[])
{
   int a, aIdx, f, i, n, y, yp, seqNum = 0, start, snum;
   double temp_logLi, tempD;
   long double tempLD;
   LargeNumber tempLN, Z_lambda, ExpFyx, fv, lambdafv;
   LargeNumber vector1[numactivities]; // vector of 1s

   for (y=0; y<numactivities; y++)
      vector1[y] = MakeLargeNumber (1.0);

   // Initialize logLi and logLiGrad
   temp_logLi = CRF_LOGLI_CONSTANT;
   for (f=0; f<numCRFFeatures; f++)
   {
      temp_logLi -= ((lambda[f] * lambda[f]) /
                     (2.0 * CRF_LOGLI_SIGMA_SQR));
      logLiGrad[f] = ((-1.0) * lambda[f] / CRF_LOGLI_SIGMA_SQR);
   }

   if (outputlevel > 1)
   {
      for (f=0; f<numCRFFeatures; f++)
         printf("  logLiGrad[%d] = %f (after init)\n", f, logLiGrad[f]);
      printf("\n");
   }

   // Process training sequences
   for (a=0; a<numactivities; a++)
   {
      for (aIdx=0; aIdx<afreq[a]; aIdx++)
      {
         if (CRF_NO_CV || (partition[seqNum] != cvnum))
         {
            start = starts[a][aIdx];
            snum = lengthactivities[a][aIdx];

            // Compute vector F(y,x) for this seq (x,y)
            // Vector F(y,x) = sum_i (vector f(y,x,i)) for this seq (x,y)
            // Matrix M_i : M_i[y,y'] = exp (lambda . vector f(y,y',x,i))
            for (f=0; f<numCRFFeatures; f++)
               CRF_Fyx[f] = MakeLargeNumber(0.0);
            for (i=0, n=0; n<snum; i++)
            {
	       // Only consider events that are part of this activity,
	       // ignore events for overlapping activities
	       if (1) /* (a == aevents[start+i][LABEL]) */
               {
                  for (y=0; y<numactivities; y++)
                     for (yp=0; yp<numactivities; yp++)
                        CRF_M[i][y][yp] = MakeLargeNumber(0.0);
                  for (f=0; f<numCRFFeatures; f++)
	          {
                                        // Compute feature's contribution to Fyx
                     yp = aevents[start+i][numfeatures-1];
                     if (i > 0)
                        y = aevents[start+i-1][numfeatures-1];
                     else y = -1;
                     fv = MakeLargeNumber(
		             EvaluateCRFFeature(f, start, i, y, yp));
                     CRF_Fyx[f] = Add(CRF_Fyx[f], fv);
                                         // Compute feature's contribution to Mi
                     yp = CRFFeatures[f].yp;
                     y = CRFFeatures[f].y;
                     fv = MakeLargeNumber(
		             EvaluateCRFFeature(f, start, i, y, yp));
                     lambdafv = Multiply(MakeLargeNumber(lambda[f]), fv);
                     if (CRFFeatures[f].type == CRF_STATE_FEATURE)
                     {
                        for (y=0; y<numactivities; y++)
                           CRF_M[i][y][CRFFeatures[f].yp] =
                              Add(CRF_M[i][y][CRFFeatures[f].yp], lambdafv);
                     }
                     else                              // CRF_TRANSITION_FEATURE
                     {
                        CRF_M[i][CRFFeatures[f].y][CRFFeatures[f].yp] =
                           Add(CRF_M[i][CRFFeatures[f].y][CRFFeatures[f].yp],
			       lambdafv);
                     }
                  }
                  for (y=0; y<numactivities; y++)             // Compute exp(Mi)
                     for (yp=0; yp<numactivities; yp++)
                     {
                        tempLD = CRF_M[i][y][yp].mantissa *
                           powl(10.0, ((long double) CRF_M[i][y][yp].exponent));
                        tempLD = expl(tempLD);
                        CRF_M[i][y][yp] = MakeLargeNumber(tempLD);
                     }
	          n++;
	       }
            }

            // Compute alphas
            //   vector alpha_i = [1], if i=0
            //                    alpha_(i-1) * M_i, if 0 < i <= n
            // Note that CRF_alpha[0] = the above alpha_1
            // Where we need alpha_0, we explicitly use vector1 or [1.0]
            VectorMatrixMult(numactivities, vector1, CRF_M[0], CRF_alpha[0]);
            for (i=1; i<snum; i++)
               VectorMatrixMult(numactivities, CRF_alpha[i-1], CRF_M[i],
                                CRF_alpha[i]);

            // Compute betas
            //   vector beta_i^T = [1], if i = n
            //                     M_(i+1) * beta_(i+1)^T, if 1 <= i < n
            // Note that CRF_beta[snum-1] = the above beta_n
            for (y=0; y<numactivities; y++)
               CRF_beta[snum-1][y] = MakeLargeNumber(1.0);
            for (i=(snum-2); i>=0; i--)
               MatrixVectorTransposeMult(numactivities, CRF_M[i+1],
                                         CRF_beta[i+1], CRF_beta[i]);

            // Compute Z_lambda(x) for this seq(x,y)
            //   Z_lambda(x) = vector alpha_n . [1]^T
            Z_lambda = MakeLargeNumber(0.0);

            for (y=0; y<numactivities; y++)
               Z_lambda = Add(Z_lambda, CRF_alpha[snum-1][y]);

            // Compute vector Exp(F(Y,x)) for this sequence
            // Exp(F(Y,x)) = sum_i(alpha_(i-1)x(f_i * M_i)xbeta_i) / Z_lambda(x)
            // Each component of Exp(F(y,x)) corresponds to a CRF feature f.
            // Note that the above formula is for f being a transition feature.
            // If f is a state feature, then the above formula becomes
            // alpha_i x f_i x beta_i / Z_lambda(x)
            for (f=0; f<numCRFFeatures; f++)
               CRF_ExpFyx[f] = MakeLargeNumber(0.0);

            for (i=0, n=0; n<snum; i++)
            {
	       // Only consider events that are part of this activity,
	       // ignore events for overlapping activities
	       if (1) /* (a == aevents[start+i][LABEL]) */
               {
                  for (f=0; f<numCRFFeatures; f++)
	          {
                     yp = CRFFeatures[f].yp;
                     y = CRFFeatures[f].y;
                     fv = MakeLargeNumber(
		             EvaluateCRFFeature(f, start, i, y, yp));

                     if (CRFFeatures[f].type == CRF_STATE_FEATURE)
                     {
                        ExpFyx = CRF_alpha[i][CRFFeatures[f].yp];
                        ExpFyx = Multiply(ExpFyx, fv);
                        ExpFyx = Multiply(ExpFyx,
			                  CRF_beta[i][CRFFeatures[f].yp]);
                     }
                     else // CRF_TRANSITION_FEATURE
                     {
                        if (i > 0)
                           ExpFyx = CRF_alpha[i-1][CRFFeatures[f].y];
                        else ExpFyx = MakeLargeNumber(1.0);
                        ExpFyx = Multiply(ExpFyx, fv);
                        ExpFyx = Multiply(ExpFyx,
                                 CRF_M[i][CRFFeatures[f].y][CRFFeatures[f].yp]);
                        ExpFyx = Multiply(ExpFyx,
			                  CRF_beta[i][CRFFeatures[f].yp]);
                     }
                     ExpFyx = Divide(ExpFyx, Z_lambda);
                     CRF_ExpFyx[f] = Add(CRF_ExpFyx[f], ExpFyx);
                  }
	          n++;
	       }
            }

            // Increment logLi by [(lambda . F(y,x)) - log Z_lamda(x)]
            // Increment vector logLiGrad by [(F(y,x) - Exp(F(Y,x))]
            tempD = (log (((double) Z_lambda.mantissa)) +
                      (Z_lambda.exponent * log (10.0)));
            temp_logLi -= tempD;

            if (outputlevel > 1)
               printf("\n    logLi = %f (after subtracting %f, seq = %d)\n",
                      temp_logLi, tempD, (seqNum+1));

            for (f=0; f<numCRFFeatures; f++)
            {
               tempLD = (CRF_Fyx[f].mantissa *
                         powl(10.0, ((long double) CRF_Fyx[f].exponent)));
               temp_logLi += (lambda[f] * ((double) tempLD));
               tempLN = Subtract(CRF_Fyx[f], CRF_ExpFyx[f]);
               tempLD = (tempLN.mantissa *
                        powl(10.0, ((long double) tempLN.exponent)));
               logLiGrad[f] += ((double) tempLD);

               if (outputlevel > 1)
               {
                  printf("    CRF_Fyx[%d] = ", f);
                  PrintLargeNumber(CRF_Fyx[f]);
                  printf("\n");
                  printf("    CRF_ExpFyx[%d] = ", f);
                  PrintLargeNumber(CRF_ExpFyx[f]);
                  printf("\n");
                  printf("    CRF_Fyx[%d] - CRF_ExpFyx[%d] = ", f, f);
                  PrintLargeNumber(tempLN);
                  printf("(%Lf)", tempLD);
                  printf("\n");
               } 
            }
         }

         if (outputlevel > 1)
         {
            // This is for each sequence
            printf("Sequence %d (length = %d):\n\n", seqNum+1,
                   lengthactivities[a][aIdx]);
            for (f=0; f < numCRFFeatures; f++) {
               if (CRF_Fyx[f].mantissa != 0.0)
	       {
                  printf("  F(y,x)[%d] =", f);
                  PrintLargeNumber(CRF_Fyx[f]);
                  printf("\n");
               }
            }
            printf("\n");

            for (i=0; i<snum; i++)
               for (y=0; y<numactivities; y++)
                  for (yp=0; yp<numactivities; yp++)
	          {
                     if ((CRF_M[i][y][yp].mantissa != 1.0) ||
                         (CRF_M[i][y][yp].exponent != 0))
		     {
                        printf("  M[%d][%d][%d] =", i, y, yp);
                        PrintLargeNumber(CRF_M[i][y][yp]);
                        printf("\n");
                     }
                  }
            printf("\n");

            for (i=0; i<snum; i++)
               for (y=0; y<numactivities; y++)
	       {
                  printf("  alpha[%d][%d] =", i, y);
                  PrintLargeNumber(CRF_alpha[i][y]);
                  printf("\n");
               }
            printf("\n");
            for (i=0; i<snum; i++)
               for (y=0; y<numactivities; y++)
	       {
                  printf("  beta[%d][%d] =", i, y);
                  PrintLargeNumber(CRF_beta[i][y]);
                  printf("\n");
               }
            printf("\n");
            printf("  Z_lambda(x) =");
            PrintLargeNumber(Z_lambda);
            printf("\n\n");
            for (f=0; f<numCRFFeatures; f++) {
               printf("  ExpF(Y,x)[%d] =", f);
               PrintLargeNumber(CRF_ExpFyx[f]);
               printf("\n");
            }
            printf("\n");
            printf("  logLi = %f\n", temp_logLi);
            printf("\n");
            for (f=0; f<numCRFFeatures; f++)
               printf("  logLiGrad[%d] = %f\n", f, logLiGrad[f]);
            printf("\n");
         }
         seqNum++;
      }
   }
   *logLi = temp_logLi;
}


// CRFTest
// cvnum = test only on activities in this partition/fold
void CRFTest(int cvnum)
{
   int i, y, a, aIdx, start, snum, seqNum, maxSeqLen;

   if (mode == TEST)
      printf("CRF Test\n");
   else printf("CRF Test (CV fold %d of %d) ...\n\n", (cvnum+1), K),

   // Find maximum activity occurrence sequence length
   // Events within sequence can have different labels
   // This could be defined by sequence length or time window
   seqNum = 0;
   maxSeqLen = 0;
   for (a=0; a<numactivities; a++)
      for (aIdx=0; aIdx<afreq[a]; aIdx++)
      {
         if (CRF_NO_CV || (partition[seqNum] == cvnum))
            if (lengthactivities[a][aIdx] > maxSeqLen)
              maxSeqLen = lengthactivities[a][aIdx];
         seqNum++;
      }

   // Print out some stats
   if (outputlevel > 0)
   {
      printf("Number of activities = %d\n", numactivities);
      printf("Number of sequences = %d\n", seqNum);
      printf("Maximum sequence length = %d\n", maxSeqLen);
      printf("\n");
   }

   // Initialize global variables
   CRF_M = (LargeNumber ***) malloc(maxSeqLen * sizeof(LargeNumber **));
   CRFViterbiProbs = (CRFViterbiProb **) malloc(maxSeqLen *
                                                sizeof(CRFViterbiProb *));
   for (i=0; i<maxSeqLen; i++) {
      CRF_M[i] = (LargeNumber **) malloc(numactivities * sizeof(LargeNumber *));
      for (y=0; y<numactivities; y++)
         CRF_M[i][y] = (LargeNumber *)
	                  malloc(numactivities * sizeof(LargeNumber));
      CRFViterbiProbs[i] = (CRFViterbiProb *) malloc(numactivities *
                                                  sizeof(CRFViterbiProb));
   }
   CRFTestSeqLabels = (int *) malloc(maxSeqLen * sizeof(int));

   // Process test sequences
   seqNum = 0;
   for (a=0; a<numactivities; a++)
   {
      for (aIdx=0; aIdx<afreq[a]; aIdx++)
      {
         if (CRF_NO_CV || (partition[seqNum] == cvnum))
         {
            start = starts[a][aIdx];
            snum = lengthactivities[a][aIdx];
	    // This time compute M based on predicted event label, not
	    // actual event label
            ComputeCRF_M(a, start, snum);
	    // Compute maximum probability of event labels for each event
	    // in the sequence
            CRFViterbi(snum);
            if (CRF_PREDICT_EVENT == 1)
                CRFEvaluateByEvent(start, snum);
            else CRFEvaluateByEventSeq(a, snum);
         }
         seqNum++;
      }
   }

   // Free global variables
   for (i=0; i<maxSeqLen; i++)
   {
      for (y=0; y<numactivities; y++)
         free(CRF_M[i][y]);
      free(CRF_M[i]);
      free(CRFViterbiProbs[i]);
   }
   free(CRF_M);
   free(CRFViterbiProbs);
   free(CRFTestSeqLabels);
}


// Compute transition matrix values
void ComputeCRF_M(int a, int start, int snum)
{
   int f, i, y, n, yp;
   long double tempLD;
   LargeNumber fv, lambdafv;

   for (i=0, n=0; n<snum; i++)
   {
      // Only consider events that are part of this activity,
      // ignore events for overlapping activities
      if (1) /* (a == aevents[start+i][LABEL]) */
      {
         for (y=0; y<numactivities; y++)
            for (yp=0; yp<numactivities; yp++)
               CRF_M[i][y][yp] = MakeLargeNumber(0.0);
         for (f=0; f<numCRFFeatures; f++)
         {
            if (CRFFeatures[f].type == CRF_STATE_FEATURE)
            {
               y = -1;
               yp = CRFFeatures[f].yp;
               fv = MakeLargeNumber(EvaluateCRFFeature(f, start, i, y, yp));
               lambdafv = Multiply(MakeLargeNumber(CRFFeatures[f].weight), fv);
               for (y=0; y<numactivities; y++)
                  CRF_M[i][y][yp] = Add(CRF_M[i][y][yp], lambdafv);
            }
            else                                       // CRF_TRANSITION_FEATURE
            {
               y = CRFFeatures[f].y;
               yp = CRFFeatures[f].yp;
               fv = MakeLargeNumber(EvaluateCRFFeature(f, start, i, y, yp));
               lambdafv = Multiply(MakeLargeNumber(CRFFeatures[f].weight), fv);
               CRF_M[i][y][yp] = Add(CRF_M[i][y][yp], lambdafv);
            }
         }
         for (y=0; y<numactivities; y++)
            for (yp=0; yp<numactivities; yp++)
            {
               tempLD = CRF_M[i][y][yp].mantissa *
                 powl(10.0, ((long double) CRF_M[i][y][yp].exponent));
               tempLD = expl(tempLD);
               CRF_M[i][y][yp] = MakeLargeNumber(tempLD);
            }
         n++;
      }
   }
}


// Compute the most likely label for each event in the sequence
void CRFViterbi(int snum)
{
   int i, y, yp, maxProbIndex;
   LargeNumber prob, maxProb;

   // Initialize label probabilities for first position in sequence
   for (yp=0; yp<numactivities; yp++)
   {
       prob = MakeLargeNumber(0.0);
       for (y=0; y<numactivities; y++)
          prob = Add(prob, CRF_M[0][y][yp]);
       CRFViterbiProbs[0][yp].prob = prob;
       CRFViterbiProbs[0][yp].label = yp;
   }

   // Compute max transition probabilities and labels for each event i
   for (i=1; i<snum; i++)
   {
      for (yp=0; yp<numactivities; yp++)
      {
         CRFViterbiProbs[i][yp].prob = MakeLargeNumber(0.0);
         CRFViterbiProbs[i][yp].label = -1;
         for (y=0; y<numactivities; y++)
         {
            prob = Multiply(CRFViterbiProbs[i-1][y].prob, CRF_M[i][y][yp]);
            if (IsGreaterThan(prob, CRFViterbiProbs[i][yp].prob))
            {
               CRFViterbiProbs[i][yp].prob = prob;
               CRFViterbiProbs[i][yp].label = y;
            }
         }
      }
   }

   // Compute most likely label for each event i in the test sequence
   maxProb = CRFViterbiProbs[snum-1][0].prob;
   maxProbIndex = 0;
   for (yp=1; yp<numactivities; yp++)
   {
      if (IsGreaterThan(CRFViterbiProbs[snum-1][yp].prob, maxProb))
      {
         maxProb = CRFViterbiProbs[snum-1][yp].prob;
         maxProbIndex = yp;
      }
   }
   CRFTestSeqLabels[snum-1] = maxProbIndex;
   for (i = (snum-2); i >= 0; i--)
   {
      CRFTestSeqLabels[i] = CRFViterbiProbs[i+1][maxProbIndex].label;
      maxProbIndex = CRFTestSeqLabels[i];
   }
}


// Determine the number of correct/incorrect label/activity predictions
// made by CRF on the given sequence.
// Assume CRFViterbi has already been called on this sequence.
void CRFEvaluateByEvent(int start, int snum)
{
   int i, actualLabel, predictedLabel;

   for (i=0; i<snum; i++)
   {
      actualLabel = aevents[start+i][numfeatures-1];
      predictedLabel = CRFTestSeqLabels[i];
      if (actualLabel == predictedLabel)
         right++;
      else wrong++;
      freq[actualLabel][predictedLabel]++;
   }
}

// Determine the activity label for the entire event sequence based
// on the most frequent activity assigned to the individual events
// in the sequence. This is compared to the given activity label.
// Assume CRFViterbi has already been called on this sequence.
void CRFEvaluateByEventSeq(int activity, int snum)
{
   int a, i, maxFreq, maxActivity, predictedFreq[numactivities];

   // Find most frequent predicted activity for test sequence events
   for (a=0; a<numactivities; a++)
      predictedFreq[a] = 0;
   for (i=0; i<snum; i++)
      predictedFreq[CRFTestSeqLabels[i]]++;
   maxFreq = predictedFreq[0];
   maxActivity = 0;
   for (a=1; a<numactivities; a++)
      if (predictedFreq[a] > maxFreq)
      {
         maxFreq = predictedFreq[a];
         maxActivity = a;
      }
   // Compare predicted activity to actual activity
   if (activity == maxActivity)
      right++;
   else wrong++;
   freq[activity][maxActivity]++;
}


// Matrix multiplies 1xd vector v1 times dxd matrix m, and stores
// the result in 1xd vector v2.
void VectorMatrixMult(int d, LargeNumber* v1, LargeNumber** m,
                      LargeNumber* v2)
{
   int r, c;
   LargeNumber tempLN;

   for (c=0; c<d; c++)
      v2[c] = MakeLargeNumber(0.0);
   for (c=0; c<d; c++)
      for (r=0; r<d; r++)
      {
         tempLN = Multiply(v1[r], m[r][c]);
         v2[c] = Add(v2[c], tempLN);
      }
}


// Matrix multiplies dxd matrix m times transpose of 1xd vector v1,
// and stores the transpose of the result in 1xd vector v2.
void MatrixVectorTransposeMult(int d, LargeNumber** m, LargeNumber* v1,
                                LargeNumber* v2)
{
   int r, c;
   LargeNumber tempLN;

   for (r=0; r<d; r++)
      v2[r] = MakeLargeNumber(0.0);
   for (r=0; r<d; r++)
      for (c=0; c<d; c++)
      {
         tempLN = Multiply(m[r][c], v1[c]);
         v2[r] = Add(v2[r], tempLN);
      }
}


// Return norm of vector v of dimension d
double CRFNorm(int d, double *v)
{
   int i;
   double sum = 0.0;

   for (i=0; i<d; i++)
     sum += (v[i] * v[i]);

   return sqrt(sum);
}


// Output the training data as rows consisting of space-delimted integer
// features with an integer class value. Useful for inputting data into
// other CRF systems.
void OutputSimpleData(FILE *fp)
{
   int a, aIdx, i, f, n, start, snum;

   // Process training sequences
   for (a=0; a<numactivities; a++)
   {
      for (aIdx=0; aIdx<afreq[a]; aIdx++)
      {
         start = starts[a][aIdx];
         snum = lengthactivities[a][aIdx];
         for (i=0, n=0; n<snum; i++)
         {
	    // Only consider events that are part of this activity,
	    // ignore events for overlapping activities
	    if (1) /* (a == aevents[start+i][LABEL]) */
            {
               // Process ith event of occurrence aIdx occurrence of activity a
               // aevents[start+i]
               for (f=0; f<numfeatures; f++)
               {
                  if (f > 0)
   	             fprintf(fp, " ");
                  fprintf(fp, "%d", aevents[start+i][f]);
               }
               fprintf(fp, "\n");
	       n++;
	    }
         }
         fprintf(fp, "\n");
      }
   }
}


// Save CRF to a file.
void SaveCRF(FILE *fp)
{
   int i;

   fprintf(fp, "%d\n", numCRFFeatures);

   for (i=0; i<numCRFFeatures; i++)
   {
      fprintf(fp, "%d\n", CRFFeatures[i].type);
      fprintf(fp, "%d\n", CRFFeatures[i].pos);
      fprintf(fp, "%d\n", CRFFeatures[i].val);
      fprintf(fp, "%d\n", CRFFeatures[i].yp);
      fprintf(fp, "%d\n", CRFFeatures[i].y);
      fprintf(fp, "%d\n", CRFFeatures[i].freq);
      fprintf(fp, "%f\n", CRFFeatures[i].weight);
   }
}


// Read CRF from a file.
void ReadCRF(FILE *fp)
{
   int i;
   float weight;

   fscanf(fp, "%d\n", &numCRFFeatures);
   CRFFeatures = (CRFFeature *) malloc(numCRFFeatures * sizeof(CRFFeature));

   for (i=0; i<numCRFFeatures; i++)
   {
      fscanf(fp, "%d\n", &CRFFeatures[i].type);
      fscanf(fp, "%d\n", &CRFFeatures[i].pos);
      fscanf(fp, "%d\n", &CRFFeatures[i].val);
      fscanf(fp, "%d\n", &CRFFeatures[i].yp);
      fscanf(fp, "%d\n", &CRFFeatures[i].y);
      fscanf(fp, "%d\n", &CRFFeatures[i].freq);
      fscanf(fp, "%f\n", &weight);
      CRFFeatures[i].weight = weight;
   }
}
