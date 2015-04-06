#ifndef MT_LSQ_H
#define MT_LSQ_H

#include "estl.h"
#include "DInst.h"
#include "Resource.h"
#include "GStats.h"
#include "MemRequest.h"
#include <queue>
#include <map>

class GProcessor;
class MemObj;
class MTStoreSet;

// [sizhuo] multi-thread/core LSQ base class
class MTLSQ {
protected:
	GProcessor *gproc; // [sizhuo] pointer to processor
	MTStoreSet *mtStoreSet; // [sizhuo] pointer to store set
	MemObj *DL1; // [sizhuo] pointer to D$

	// [sizhuo] max ld/st number
	const int32_t maxLdNum;
	const int32_t maxStNum;
	// [sizhuo] fre ld/st entries
	int32_t freeLdNum;
	int32_t freeStNum;
	// [sizhuo] forward delay
	const TimeDelta_t ldldForwardDelay;
	const TimeDelta_t stldForwardDelay;

	// [sizhuo] pending event Q type
	typedef std::queue<CallbackBase*> PendQ;

	// [sizhuo] speculative LSQ hold load/store still in ROB (speculative, can be killed)
	// load can have all 3 states
	// store only Done state
	typedef enum {
		Wait, // [sizhuo] info (e.g. addr) filled in, but haven't issued to memory
		Exe, // [sizhuo] executing in memory OR bypassing data
		Done // [sizhuo] finished execution
	} SpecLSQState;

	class SpecLSQEntry {
	public:
		DInst *dinst;
		SpecLSQState state;
		bool needReEx; // [sizhuo] memory dependency violation detected while executing in memory
		PendQ pendRetireQ; // [sizhuo] events stalled unitl this RECONCILE fence retires
		PendQ pendExQ; // [sizhuo] events stalled until this LOAD finishes execution

		SpecLSQEntry() : dinst(0), state(Wait), needReEx(false) {}
		void clear() {
			dinst = 0;
			state = Wait;
			needReEx = false;
			I(pendRetireQ.empty());
			I(pendExQ.empty());
		}
	};

	// [sizhuo] pool of SpecLSQ entries
	pool<SpecLSQEntry> specLSQEntryPool;

	typedef std::map<Time_t, SpecLSQEntry*> SpecLSQ;
	SpecLSQ specLSQ;

	// [sizhuo] commited SQ holds stores retired from ROB (non-speculative)
	class ComSQEntry {
	public:
		AddrType addr;
		bool doStats;
		ComSQEntry() : addr(0), doStats(true) {}
		void clear() {
			addr = 0;
			doStats = true;
		}
	};

	// [sizhuo] pool of comSQ entries
	pool<ComSQEntry> comSQEntryPool; 

	typedef std::map<Time_t, ComSQEntry*> ComSQ;
	ComSQ comSQ;

	// [sizhuo] fully pipelined contention port for executing Load
	PortGeneric *ldExPort;

	// [sizhuo] execute a load
	virtual void ldExecute(DInst *dinst) = 0;
	typedef CallbackMember1<MTLSQ, DInst*, &MTLSQ::ldExecute> ldExecuteCB;

	// [sizhuo] due to contention on load ex port, we need to function to schedule load ex
	void scheduleLdEx(DInst *dinst);
	typedef CallbackMember1<MTLSQ, DInst*, &MTLSQ::scheduleLdEx> scheduleLdExCB;

	// [sizhuo] when a load finishes execution
	virtual void ldDone(DInst *dinst) = 0;
	typedef CallbackMember1<MTLSQ, DInst*, &MTLSQ::ldDone> ldDoneCB;

	// [sizhuo] fully pipelined contention port for issuing store to memory
	PortGeneric *stToMemPort;

	// [sizhuo] issue store to memory
	void stToMem(AddrType addr, Time_t id, bool doStats) {
		MemRequest::sendReqWrite(DL1, doStats, addr, stCommitedCB::create(this, id));
	}
	typedef CallbackMember3<MTLSQ, AddrType, Time_t, bool, &MTLSQ::stToMem> stToMemCB;

	// [sizhuo] when a store commited to memory, we retire entry from comSQ
	// and send next oldest store to same addr to memory
	virtual void stCommited(Time_t id) = 0;
	typedef CallbackMember1<MTLSQ, Time_t, &MTLSQ::stCommited> stCommitedCB;

	// [sizhuo] XXX: we don't need contention port for ldDone & stCommited
	// they are limited by when we send ack in ACache
	// for load, we fill in data array or directly read data array
	// for store, we write data array
	// so they will contend for data array port in ACache
	
	// [sizhuo] Stats counters
	GStatsCntr nLdKillByLd;
	GStatsCntr nLdKillBySt;
	GStatsCntr nLdKillByInv;
	GStatsCntr nLdReExByLd;
	GStatsCntr nLdReExBySt;
	GStatsCntr nLdReExByInv;
	GStatsCntr nStLdForward;
	GStatsCntr nLdLdForward;

	// [sizhuo] helper to remove poisoned entry & reset
	void removePoisonedEntry(SpecLSQ::iterator rmIter);
	void removePoisonedInst(DInst *dinst);

public:
	MTLSQ(GProcessor *gproc_);
	virtual ~MTLSQ() {}

	// [sizhuo] add new entry when inst is enq to ROB
	virtual StallCause addEntry(DInst *dinst) = 0;
	// [sizhuo] issue to LSQ: fill in info, check memory dependency violation
	// then LSQ will try to execute this inst
	// After execution, will call executed() of the resource
	// XXX: contention for issue is modelled in Resource::executing
	virtual void issue(DInst *dinst) = 0;
	typedef CallbackMember1<MTLSQ, DInst*, &MTLSQ::issue> issueCB;
	// [sizhuo] retire entry from speculative LSQ
	virtual bool retire(DInst *dinst) = 0;
	// [sizhuo] cache invalidation may kill loads
	virtual void cacheInv(AddrType addr) = 0;
	typedef CallbackMember1<MTLSQ, AddrType, &MTLSQ::cacheInv> cacheInvCB;
	// [sizhuo] for reset when execption happens
	virtual void reset() = 0;
	virtual bool isReset() = 0;

	// [sizhuo] creator function
	static MTLSQ *create(GProcessor *gproc_);
};

// [sizhuo] LSQ for WMM
// 
// reconcile fence is added to LSQ when added to cluster (Resource::canIssue -- addEntry)
//
// commit fence is NOT added to LSQ
// 
// load/store are added when data dependency is resolved (Resource::executing -- issueCB)
// but load/store will reduce free entry num in Resource::canIssue -- addEntry
// 
// for LL & SC & commit fence, we use processor retire stage to prompt its execution
// DON'T let them depend on commited store queue, it's hard to flush
// 
// FIXME: currently there is no LL/SC generated by emulator
// so we don't handle them
class WMMLSQ : public MTLSQ {
protected:
	virtual void ldExecute(DInst *dinst);
	virtual void ldDone(DInst *dinst);
	virtual void stCommited(Time_t id);
public:
	WMMLSQ(GProcessor *gproc_) : MTLSQ(gproc_) {}
	virtual ~WMMLSQ() {}

	virtual StallCause addEntry(DInst *dinst);
	virtual void issue(DInst *dinst);
	virtual bool retire(DInst *dinst);
	virtual void cacheInv(AddrType addr) {}
	virtual void reset();
	virtual bool isReset();
};

#endif
