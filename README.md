## Verifying Equivalence of Spark Programs - Artifact
---------------------------------------------------

+ _32bit Ubuntu 16.04 with 1GB RAM._
+ _Prepared on a 64bit Windows host with 32GB RAM and 8 cores, 3.4GHz._
+ _It has Python2.7 with pip, and Z3 installed._
+ _Credentials are user/pass._

1. After booting the image, open the terminal and run the ```./run_artifact.sh``` file, located in the home directory _/home/user_.
This will show the output of the Python-based tool on the full testcases (as presented in the Technical Report following this paper).

2. Source code can be located in **/home/user/src**. It has some documentation.
Note that some of the functions refer to names of verification methods that evolved and changed a little bit.

3. Examples code can be found in the /home/user/src/test directory.

4. Adding a new test requires adding a new test to the test_dict dictionary, in this template:
   
    ```id: (Tester(f1, f2, rdd_of_matching_type), expected, "P", "Q")```
    
    where _expected_ should be a string equal to either "equivalent" or "Not equivalent".
A specific test can be run with the ```run_specific_test(id)``` function.

### An overview of the tests
In tester.py, each line of code containing a test includes the name of the programs as they appear 
in the accompanying Technical Report, Section 15.
Tests 1-6 are all NoAgg tests. 
When programs are not equivalent, note the given value to ```x1...,x2...``` variables which are the input bags' representative elements.
The other variables are intermediate results in the programs.
When the model is empty it means any assignment shows the inequivalence.

Tests 7-12 are all either AggOne or AggOneSync. 
Test 16 is AggOne but not AggOneSync but the equivalence is correctly detected.
Test 13 is AggOne, not AggOneSync, and the tool is unable to prove the equivalence (see Section 5, regarding P15'' an P16'').
The rest of the tests in 7-12 are all AggOneSync.
In counterexamples to equivalence in these examples, note 
the ```x1...``` variables (first fold step), 
and the ```x1...r...``` variables  (second fold step)

Tests 17-20 are NoAgg but focus on join and on bags with more complicated record types.
The purpose of these tests is to check the parsing abilities of the tool.
The equivalence is checked per each component of the tuple,
 thus the message "Equivalent!" is printed multiple times for equivalent examples.
If there is not an equal structure of the tuples, the tool will output "not equivalent".
If a pair of corresponding components are not equivalent but the others are, the tool prints for each the result, and a pair of programs can be understood as equivalent if all of their output components are equivalent.

Tests 21-23 focus solely on AggOneK, by a reduction to a simpler class as introduced in the last example of Section 1 (Overview), and fully specified in Section 14 of the accompanying Technical Report.

### Flow, and main building blocks
1. The input is comprised of two Python functions. Each module (compilation unit) pertaining to the function is analyzed in order for the tool to be able to analyze UDFs and create terms.

2. After analyzing the UDFs the program terms are created (see SparkConverter).
_Program terms may be tuples of tuples, so there is an analysis of the return term and we iterate on the components._
    _If tuple types are not the same, we are obviously not equivalent and the tool detects it._
A component of the program term tuple may be a ```FoldResult``` term or a 'regular' term.

3. When no fold operations are performed, verification is quite straight-forward (```verifyEquivalentElements```).
Variables are "Boxed" in the sense they have both an integer variable and a boolean "isBot" variable.
Each operation such as map/filter creates new variables with updated fields (value/isBot, as relevant).
Cartesian products and tuples are (currently) managed manually and are not "Boxed".
    _(This causes a degree of complexity in the fold handling as well and should be noted._
    _It's a prototype tool, but it should be generalized for better flexibility and extendibility.)_

4. When fold operations are part of the term it is more complicated. The term is not an actual first order term, thus we keep
a context with metadata such as the fold function, init value and others, the aforementioned class ```FoldResult```.
We handle these in ```verifyEquivalentFolds```.
4.1. The first step is checking if these are AggOneSync (```isAgg1pairsync```). If yes, we return the result of ```verifyEquivalentSyncfolds```.
4.2. For regular AggOne instances, we generate all the required terms for the inductive argument and add the required formulas that define
what is an intermediate value, what is the value of applying a new term on the intermediate value with the fold function, etc...
This requires 'refreshing' some of the variable names and some bookkeeping which we will not delve into.
We generate two formulas:

    (1) init values match

    (2) Equivalence in an inductive argument as presented in the paper

    We then ask the solver if Not ((1) and (2)) is satisfiable.

4.3. For AggOneSync the process of both checking the semantic restriction and the equivalence condition is done in a similar
manner, albeit more complex. Mainly because we need to quantify on all the variables for Z3 to succeed.

4.4. ByKey example work according to the reduction defined in the paper, except that we did not implement "Isomorphic Keys" check which is required for soundness.
_This is a limitation of the prototype tool._

5. Another class of interest is ```UDFConverter``` in UDFParser.py. It is very technical but it allows to re-use UDFs for substituting different terms in them.
It works on Python code in imperative/Object-Oriented style (like real Spark).