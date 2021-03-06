#ifndef WMMRESOURCE_H
#define WMMRESOURCE_H

#include "GStats.h"
#include "Resource.h"
#include "nanassert.h"
#include "callback.h"

class MemObj;
class MTStoreSet;
class MTLSQ;

class WMMFURALU : public Resource {
  GStatsCntr memoryBarrier;
  Time_t blockUntil;

protected:
public:
  WMMFURALU(Cluster *cls, PortGeneric *aGen, TimeDelta_t l, int32_t id);

  StallCause canIssue(DInst  *dinst);
  void       executing(DInst *dinst);
  void       executed(DInst  *dinst);
  bool       preretire(DInst *dinst, bool flushing);
  bool       retire(DInst    *dinst, bool flushing);
  void       performed(DInst *dinst);
	// [sizhuo] no need for recovery from ROB flush
	virtual void reset() {}
	virtual bool isReset() { return true; }
};

class WMMLSResource : public Resource {
protected:
	MTLSQ *mtLSQ;
	MTStoreSet *mtStoreSet;
	
public:
	WMMLSResource(Cluster *cls, PortGeneric *aGen, TimeDelta_t l, MTLSQ *q, MTStoreSet *ss, int32_t id);
};

class WMMFULoad : public WMMLSResource {
public:
	WMMFULoad(Cluster *cls, PortGeneric *aGen, TimeDelta_t l, MTLSQ *q, MTStoreSet *ss, int32_t id);

  StallCause canIssue(DInst  *dinst);
  void       executing(DInst *dinst);
  void       executed(DInst  *dinst);
  bool       preretire(DInst  *dinst, bool flushing);
  bool       retire(DInst    *dinst,  bool flushing);
  void       performed(DInst *dinst);
	// [sizhuo] no need for recovery when ROB flush
	virtual void reset() {}
	virtual bool isReset() { return true; }
};

class WMMFUStore : public WMMLSResource {
public:
	WMMFUStore(Cluster *cls, PortGeneric *aGen, TimeDelta_t l, MTLSQ *q, MTStoreSet *ss, int32_t id);

  StallCause canIssue(DInst  *dinst);
  void       executing(DInst *dinst);
  void       executed(DInst  *dinst);
  bool       preretire(DInst  *dinst, bool flushing);
  bool       retire(DInst    *dinst,  bool flushing);
  void       performed(DInst *dinst);
	// [sizhuo] no need for recovery when ROB flush
	virtual void reset() {}
	virtual bool isReset() { return true; }
};

#endif
