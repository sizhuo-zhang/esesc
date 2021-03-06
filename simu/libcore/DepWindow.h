// Contributed by Jose Renau
//
// The ESESC/BSD License
//
// Copyright (c) 2005-2013, Regents of the University of California and 
// the ESESC Project.
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//
//   - Redistributions of source code must retain the above copyright notice,
//   this list of conditions and the following disclaimer.
//
//   - Redistributions in binary form must reproduce the above copyright
//   notice, this list of conditions and the following disclaimer in the
//   documentation and/or other materials provided with the distribution.
//
//   - Neither the name of the University of California, Santa Cruz nor the
//   names of its contributors may be used to endorse or promote products
//   derived from this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
// ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
// LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
// CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
// SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
// INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
// CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
// ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
// POSSIBILITY OF SUCH DAMAGE.

#ifndef DEPWINDOW_H
#define DEPWINDOW_H

#include "nanassert.h"

#include "Resource.h"
#include "Port.h"

class DInst;
class GProcessor;
class Cluster;

// [sizhuo] issue window (reservation station) in one cluster
class DepWindow {
private:
  GProcessor *gproc; // [sizhuo] processor it belongs to
  Cluster    *srcCluster; // [sizhuo] cluster it belongs to

  const int32_t Id;

  // [sizhuo] all kinds of delay
  const TimeDelta_t InterClusterLat;
  const TimeDelta_t WakeUpDelay;
  const TimeDelta_t SchedDelay;
  const TimeDelta_t RegFileDelay;

  GStatsCntr wrForwardBus;

  // [sizhuo] ports to model contention
  PortGeneric *wakeUpPort;
  PortGeneric *schedPort;

protected:
  void preSelect(DInst *dinst);

public:
  ~DepWindow();
  DepWindow(GProcessor *gp, Cluster *aCluster, const char *clusterName);

  void wakeUpDeps(DInst *dinst); // [sizhuo] increase wakeup time for inst depending on dinst

  void select(DInst *dinst); // [sizhuo] select inst for execution

  StallCause canIssue(DInst *dinst) const; // [sizhuo] always return NoStall...
  void addInst(DInst *dinst); // [sizhuo] add new inst into this window
  // [sizhuo] things to do when dinst finishes execution: wakeup inst depending on dinst when dinst finish execution
  void executed(DInst *dinst); 

	// [sizhuo] resolve memory dependency
	void resolveMemDep(DInst *dinst);

	// [sizhuo] recover depWindow stats when flushing
	// actually there is no state to recover
	void reset() {}
	bool isReset() { return true; }
};

#endif // DEPWINDOW_H
