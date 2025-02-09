---
title: Writing a MILP Solver From Scratch Part 1 - Reading MPS 
layout: post
category: software
image: assets/images/punchcard.jpg
---

Soon after I started working on mixed integer linear programs (MILPs), it became obvious that the representation of the problem is very important for the mathematical solver to be able to find a solution fast without using too much resources. There are many ways to represent a problem and it is not always clear which one is the best. It takes a great amount of experience and knowledge about the underlying processes to get it right.

I thought a good (and fun) way to understand how to write better models would be to write a MILP solver from scratch to teach myself the fundamentals of it. It is not necessarily a hard thing to do as the process of solving a mixed integer linear program is very well known. [There are many mathematical solvers](https://web.archive.org/web/20250105160933/https://plato.asu.edu/ftp/milp_old.html), the best ones being the commercial ones. The open source alternatives are strong enough to solve small to medium size problems, but often take a very long time for large problems.

In this blog series I will attempt to write yet another MILP solver. Obviously the goal of this solver is not to be the best or the fastest. The goal is to be able to create one from scratch and understand the basics of linear programs. 

Here is the agenda for this blog series:

- Part 1: Reading the mathematical model
- Part 2: Solving the relaxed problem: Simplex Algorithm
- Part 3: Finding an integer solution to the problem

## The programming language of choice: Go

I'm writing a MILP solver to learn about MILPs but also to experiment with a new (to me) programming language: Go

I hope to leverage Go's "goroutines" in the 3rd part of this journey, while finding an integer solution to the problem. Finding an integer solution requires constructing a "branch and bound" tree where each node of the tree has some of the variables fixed to an integer value and the LP solution is applied to the rest of the variables. This process could benefit a lot from searching the tree concurrently. I think Go's concurrency tools will be useful while solving this problem.

## Defining LP/MILP models

Linear programming is an old problem. The problem of solving a system of linear inequalities dates back to 1827, when Fourier published a method to eliminate variables (a.k.a, [Fourier-Motzking elimination](https://en.wikipedia.org/wiki/Fourier%E2%80%93Motzkin_elimination)), much earlier than Dantzig's Simplex method in 1947. 

The conseuqence of this is having file formats that are designed for old systems. MPS file format is the most widely used format for LP/MILPs and it looks like this:

```
NAME          TESTPROB
ROWS
 N  COST
 L  LIM1
 G  LIM2
 E  MYEQN
COLUMNS
    XONE      COST                 1   LIM1                 1
    XONE      LIM2                 1
    YTWO      COST                 4   LIM1                 1
    YTWO      MYEQN               -1
    ZTHREE    COST                 9   LIM2                 1
    ZTHREE    MYEQN                1
RHS
    RHS1      LIM1                 5   LIM2                10
    RHS1      MYEQN                7
BOUNDS
 UP BND1      XONE                 4
 LO BND1      YTWO                -1
 UP BND1      YTWO                 1
ENDATA
```


This problem can also be written in a much more human-readable format like the following:

```
min: +XONE +4 YTWO +9 ZTHREE;
LIM1: +XONE +YTWO <= 5;
LIM2: +XONE +ZTHREE >= 10;
MYEQN: -YTWO +ZTHREE = 7;
XONE <= 4;
YTWO >= -1;
YTWO <= 1;
```
(LP file format, from LP Solve's  [MPS file format documentation](https://lpsolve.sourceforge.net/5.0/mps-format.htm) )

Despite the obvious benefits of the latter, the industry is still using MPS format widely. For my solver, I will only implement a reader
for the MPS file format, as my main goal is to create a solver that can solve some of the benchmark instances from [MIPLIB benchmark library](https://miplib.zib.de/), which are always in MPS format.

## Reading MPS format

MPS is a relatively easy format to parse. The file has 6 sections (ROWS, COLUMNS, and RHS are required; RANGES, BOUNDS and SOS are optional), where each section can have a different number of columns. LP Solve's [MPS file format documentation](https://lpsolve.sourceforge.net/5.0/mps-format.htm) is the best I found online to understand the file format deeply. 

### Rows

The "Rows" section defines the names and the types of each constraint. The names are arbitrary user defined names. Types can be E for equality, L for less than or equal to (<=), and G for greater than or equal to (>=).

### Columns

The "Columns" section defines where each column (or variable) is put to which rows (constraints). This is generally the largest part of the MPS file
since it needs to have an input for all the column to row assignments. Any unmentioned assignment is assumed to have a coefficient of zero in the row.

In addition, any variable that is an integer needs to be within the INTORG and INTEND markers. Every other variable is assumed to be non integer.

### RHS

The "Right Hand Side (RHS)" section defines the right hand side of the constraints. For example, if the model expresses a constraint like `XONE <= 4`, the right hand side would be 4.

### Bounds

The "Bounds" section defines the limits of each variable. By default, all columns are assumed to be positive (or have a bound 0 <= x <= infinity). For all other variable level constraints, a bound can be expressed in many types (such as LO for lower bound or UP for upper bound).

## Output of the MPS reader

The job of the MPS reader is to read all the sections above and to produce 3 pieces of information: coefficiencts for the objective function (c), the right hand side of the constraints (b), and the constraint matrix (A). The names of these pieces are conventinally named as c, b, and A; which is important to know to understand any content online related to LP and Simplex algorithm.

I was able to write an MPS reader program that takes an mps file path and returns c,b, and A in about ~300 lines of code. To continue on the example MPS file I showed above, here is the output of the MPS reader program:

```
c: [1 -4 9 0 0 0 0 0]
b: [5 10 7 4 1 1]
A: [[1 -1 0 1  0 0  0 0] 
    [1 -0 1 0 -1 0  0 0] 
    [0  1 1 0  0 0  0 0] 
    [1 -0 0 0  0 1  0 0] 
    [0  1 0 0  0 0 -1 0] 
    [0  1 0 0  0 0  0 1]]
```

If you're careful, you'll realize that there are way more coefficients in the output than variables in the MPS file. This is because the MPS reader program also adds the slack variables to the output to conveniently pass these vectors and the A matrix to the Simplex implementation. 

## Testing the MPS reader

Now that I have an MPS reader that can read the simplest MPS file in the world. I have unit tests covering most of the implementation, so I am fairly confident that the reader is doing the right thing. I can only read both the MPS file and the output to decide if it's doing the right thing. However, despite the unit tests I have, it's hard to know if this program could read all kinds of different MPS files in the wild. 

Thankfully the benchmarking framework I mentioned above is also a great library for testing. At the end of the day, if the program reads all MPS files from the benchmarking set and gives a correct result, we're good. I got the list of "easy" problems from the [MIPLIB](https://miplib.zib.de/) library, put it in the "miplib_easy.txt" and wrote a little bash script to download them all:

```
while read -r line; do
    wget -O "$line.mps.gz" "https://miplib.zib.de/WebData/instances/$line.mps.gz"
    gunzip "$line.mps.gz"
done < "miplib_easy.txt"
```

I created a `_test.go` file in the mpsreader package and read all these files and do a couple of simple checks:

```
func TestMpsReaderWithFiles(t *testing.T) {
	testfiles, err := os.ReadDir("../testfiles")
	if err != nil {
		t.Errorf("Error reading directory: %v", err)
		return
	}

	for idx, mpsfile := range testfiles {

		c, A, b, err := ReadMPS("../testfiles/" + mpsfile)

		if err != nil {
			t.Errorf("Error reading MPS file %s: %v", mpsfile, err)
		}

		rows, cols := len(A), len(A[0])

		if cols != len(c) {
			t.Errorf("Number of columns in A should be equal to length of c: %d, %d", cols, len(c))
		}

		if rows != len(b) {
			t.Errorf("Number of rows in A should be equal to length of b: %d, %d", rows, len(b))
		}

		fmt.Printf("File read successfully: %s (%d/%d) \n", mpsfile, idx+1, len(mpsfiles))

	}
}
```

Now I can just run `go test`:

```
...
File read successfully: timtab1.mps (100/100) 
PASS
ok      github.com/kutlay/gosolver/mpsreader    1.837s
```

Yay!

I find it very useful to add this piece of code that runs all the MPS files as a test. Writing it as a test instead of a regular program allows me to benefit from Go's testing tools with no effort. These test are now part of my regular tests. I run them each time I make a change in the code. This increases my confidence that the program works successfully for a large set of inputs.

Additionally, I can run `go test -cpuprofile cpu.prof -memprofile mem.prof -bench .` to get the CPU and memory profile of my program to understand where it spends the most time and memory. The diverse set of MPS files help me to understand which part of the program could benefit from optimization on average.

Even though this helps me a lot to improve the MPS reader implementation, it doesn't guarantee correctness for the resulting vectors and the A matrix. The correctness could be guaranteed only by giving the output is given to a solver and comparing the solution with the known solution of the problem. 

Obviously, this requires to have a functioning solver. That brings us to the second part of the blog series: "Solving MILP From Scratch Part 2 - Simplex Algorithm". I plan to publish Part 2 in April 2025. Stay tuned!