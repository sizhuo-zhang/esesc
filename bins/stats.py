#!/usr/bin/python
import re
import scipy.io as sio
import sys
import os
import json

# check arg
if len(sys.argv) < 2:
	print 'Usage: ./stats.py <esesc result file> [output folder]'
	sys.exit()

if not os.path.isfile(sys.argv[1]):
	print 'ERROR: cannot find {}'.format(sys.argv[1])
	sys.exit()

# read file
fp = open(sys.argv[1], 'r')
resultFile = list(fp)
fp.close()

# data to save
saveData = {}

# get basic param
coreNum = -1
maxLd = -1
maxSt = -1
robSize = -1
retireWidth = -1
issueWidth = -1
verifyLd = -1

for line in resultFile:
	if coreNum == -1:
		m = re.search(r'cpusimu\[0:(\d+)\]', line)
		if m:
			coreNum = int(m.group(1)) + 1
			continue
		m = re.search(r'cpusimu\[0\]', line)
		if m:
			coreNum = 1
			continue
	if maxLd == -1:
		m = re.search(r'maxLoads\s*=\s*(\d+)', line)
		if m:
			maxLd = int(m.group(1))
			continue
	if maxSt == -1:
		m = re.search(r'maxStores\s*=\s*(\d+)', line)
		if m:
			maxSt = int(m.group(1))
			continue
	if robSize == -1:
		m = re.search(r'robSize\s*=\s*(\d+)', line)
		if m:
			robSize = int(m.group(1))
	if retireWidth == -1:
		m = re.search(r'retireWidth\s*=\s*(\d+)', line)
		if m:
			retireWidth = int(m.group(1))
			continue
	if issueWidth == -1:
		m = re.search(r'issueWidth\s*=\s*(\d+)', line)
		if m:
			issueWidth = int(m.group(1))
			continue
	if verifyLd == -1:
		m = re.search(r'sctsoVerifyLd\s*=\s*(true|false)', line)
		if m:
			verifyLd = int(m.group(1) == 'true')
			continue
	if coreNum > 0 and maxLd > 0 and maxSt > 0 and robSize > 0 and retireWidth > 0 and issueWidth > 0 and verifyLd >= 0:
		break;

saveData['coreNum'] = coreNum
saveData['maxLd'] = maxLd
saveData['maxSt'] = maxSt
saveData['robSize'] = robSize
saveData['retireWidth'] = retireWidth
saveData['issueWidth'] = issueWidth
saveData['verifyLd'] = verifyLd

print ''

# overall performance
wallClock = -1
simTime = -1
inst = [-1] * coreNum
cycle = [-1] * coreNum

for line in resultFile:
	if wallClock == -1:
		m = re.search(r'OS:wallClock\s*=\s*(\d+)\.0+', line)
		if m:
			wallClock = int(m.group(1))
			continue
	if simTime == -1:
		m = re.search(r'OS:simTime\s*=\s*(\d+)\.0+', line)
		if m:
			simTime = int(m.group(1))
			continue
	m = re.search(r'P\((\d+)\):nCommitted\s*=\s*(\d+)\.0+', line)
	if m:
		inst[int(m.group(1))] = int(m.group(2))
		continue
	m = re.search(r'P\((\d+)\)_activeCyc\s*=\s*(\d+)\.0+', line)
	if m:
		cycle[int(m.group(1))] = int(m.group(2))
		continue
	if (reduce(lambda acc, x: (acc and x > -1), inst, True) and
			reduce(lambda acc, x: (acc and x > -1), cycle, True) and
			wallClock > -1 and simTime > -1):
		break

saveData['wallClock'] = wallClock
saveData['simTime'] = simTime
saveData['inst'] = inst
saveData['cycle'] = cycle

print '-- Overall Peformanace'
print 'wallClock = {}, simTime = {}'.format(wallClock, simTime)
print '{:<6s}{:<14s}{:<14s}{:<14s}'.format(' ', 'cycle', 'inst', 'IPC')
for i in range(0, coreNum):
	print '{:<6s}{:<14d}{:<14d}{:<14s}'.format('P({})'.format(i),
			cycle[i], inst[i], 'nan' if cycle[i] <= 0 else '{:<14.2f}'.format(float(inst[i]) / float(cycle[i])))
print ''

# inst distribution
nRALU = [0] * coreNum
nAALU = [0] * coreNum
nBALU = [0] * coreNum
nLALU_LD = [0] * coreNum
nLALU_REC = [0] * coreNum
nSALU_ST = [0] * coreNum
nSALU_ADDR = [0] * coreNum
nSALU_COM = [0] * coreNum
nCALU_3C = [0] * coreNum
nCALU_5C = [0] * coreNum
nCALU_7C = [0] * coreNum
nMALU = [0] * coreNum

for line in resultFile:
	m = re.search(r'P\((\d+)\)_ExeEngine_i(\w+):n=(\d+)\.0+', line)
	if m:
		coreId = int(m.group(1))
		instType = m.group(2)
		count = int(m.group(3))
		if instType == 'RALU':
			nRALU[coreId] = count
		elif instType == 'AALU':
			nAALU[coreId] = count
		elif re.search(r'^BALU', instType):
			nBALU[coreId] += count
		elif instType == 'LALU_LD':
			nLALU_LD[coreId] = count
		elif instType == 'LALU_REC':
			nLALU_REC[coreId] = count
		elif instType == 'SALU_ST':
			nSALU_ST[coreId] = count
		elif instType == 'SALU_ADDR':
			nSALU_ADDR[coreId] = count
		elif instType == 'SALU_COM':
			nSALU_COM[coreId] = count
		elif instType == 'CALU_FPALU' or instType == 'CALU_MULT':
			nCALU_3C[coreId] += count
		elif instType == 'CALU_FPMULT':
			nCALU_5C[coreId] += count
		elif instType == 'CALU_FPDIV' or instType == 'CALU_DIV':
			nCALU_7C[coreId] += count
		elif re.search(r'^MALU', instType):
			nMALU[coreId] += count
		else:
			if count > 0:
				print 'ERROR: unknow inst type {}'.format(instType)
				sys.exit()

saveData['nRALU'] = nRALU
saveData['nAALU'] = nAALU
saveData['nBALU'] = nBALU
saveData['nLALU_LD'] = nLALU_LD
saveData['nLALU_REC'] = nLALU_REC
saveData['nSALU_ST'] = nSALU_ST
saveData['nSALU_ADDR'] = nSALU_ADDR
saveData['nSALU_COM'] = nSALU_COM
saveData['nCALU_3C'] = nCALU_3C
saveData['nCALU_5C'] = nCALU_5C
saveData['nCALU_7C'] = nCALU_7C
saveData['nMALU'] = nMALU

print '-- Instruction Distribution'
print '{:<6s}{:<6s}{:<6s}{:<6s}{:<9s}{:<10s}{:<9s}{:<11s}{:<10s}{:<9s}{:<9s}{:<9s}{:<6s}'.format('(%)', 
'RALU', 'AALU', 'BALU', 'LALU_LD', 'LALU_REC', 'SALU_ST', 'SALU_ADDR', 'SALU_COM', 'CALU_3C', 'CALU_5C', 'CALU_7C', 'MALU')
for i in range(0, coreNum):
	if inst[i] <= 0:
		print '{:<6s}{:<6s}{:<6s}{:<6s}{:<9s}{:<10s}{:<9s}{:<11s}{:<10s}{:<9s}{:<9s}{:<9s}{:<6s}'.format('P({})'.format(i),
				'nan', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan')
	else:
		print '{:<6s}{:<6.2f}{:<6.1f}{:<6.1f}{:<9.1f}{:<10.3f}{:<9.1f}{:<11.1f}{:<10.3f}{:<9.1f}{:<9.1f}{:<9.1f}{:<6.1f}'.format('P({})'.format(i),
				float(nRALU[i]) / float(inst[i]) * 100.0, float(nAALU[i]) / float(inst[i]) * 100.0, float(nBALU[i]) / float(inst[i]) * 100.0,
				float(nLALU_LD[i]) / float(inst[i]) * 100.0, float(nLALU_REC[i]) / float(inst[i]) * 100.0,
				float(nSALU_ST[i]) / float(inst[i]) * 100.0, float(nSALU_ADDR[i]) / float(inst[i]) * 100.0,
				float(nSALU_COM[i]) / float(inst[i]) * 100.0, float(nCALU_3C[i]) / float(inst[i]) * 100.0, 
				float(nCALU_5C[i]) / float(inst[i]) * 100.0, float(nCALU_7C[i]) / float(inst[i]) * 100.0, float(nMALU[i]) / float(inst[i]) * 100.0)
print ''

# unaligned memory access
unalignLd = [0] * coreNum
unalignSt = [0] * coreNum

for line in resultFile:
	m = re.search(r'P\((\d+)\)_MTLSQ_nUnalign(Ld|St)\s*=\s*(\d+)\.0+', line)
	if m:
		coreId = int(m.group(1))
		count = int(m.group(3))
		if m.group(2) == 'Ld':
			unalignLd[coreId] = count
		elif m.group(2) == 'St':
			unalignSt[coreId] = count
		else:
			print 'ERROR: unknow unalign type {}'.format(m.group(2))
			sys.exit()

saveData['unalignLd'] = unalignLd
saveData['unalignSt'] = unalignSt

print '-- Unaligned Memory Access'
print '{:<6s}{:<14s}{:<14s}'.format('', 'Unalign Ld%', 'Unalign St%')
for i in range(0, coreNum):
	print '{:<6s}{:<14s}{:<14s}'.format('P({})'.format(i),
			'nan' if nLALU_LD[i] <= 0 else '{:<14.3f}'.format(float(unalignLd[i]) / float(nLALU_LD[i]) * 100.0),
			'nan' if nSALU_ST[i] <= 0 else '{:<14.3f}'.format(float(unalignSt[i]) / float(nSALU_ST[i]) * 100.0))
print ''

# retire port stall
retireStallByExLd = [0] * coreNum
retireStallByExOther = [0] * coreNum
retireStallByFlushInv = [0] * coreNum
retireStallByFlushRep = [0] * coreNum
retireStallByFlushSt = [0] * coreNum
retireStallByFlushLd = [0] * coreNum
retireStallByComSQ = [0] * coreNum
retireStallByEmpty = [0] * coreNum
retireStallByVerifyInv = [0] * coreNum
retireStallByVerifyRep = [0] * coreNum
retireStallByVerifyLd = [0] * coreNum
retireStallByVerifySt = [0] * coreNum

for line in resultFile:
	m = re.search(r'P\((\d+)\)_retireStallBy(\w+)\s*=\s*(\d+)\.0+', line)
	if m:
		coreId = int(m.group(1))
		stallType = m.group(2)
		count = int(m.group(3))
		if stallType == 'Empty':
			retireStallByEmpty[coreId] = count
		elif stallType == 'ComSQ':
			retireStallByComSQ[coreId] = count
		elif stallType == 'Flush_CacheInv':
			retireStallByFlushInv[coreId] = count
		elif stallType == 'Flush_CacheRep':
			retireStallByFlushRep[coreId] = count
		elif stallType == 'Flush_Load':
			retireStallByFlushLd[coreId] = count
		elif stallType == 'Flush_Store':
			retireStallByFlushSt[coreId] = count
		elif stallType == 'Verify_CacheInv':
			retireStallByVerifyInv[coreId] = count
		elif stallType == 'Verify_CacheRep':
			retireStallByVerifyRep[coreId] = count
		elif stallType == 'Verify_Load':
			retireStallByVerifyLd[coreId] = count
		elif stallType == 'Verify_Store':
			retireStallByVerifySt[coreId] = count
		elif stallType == 'Ex_iLALU_LD':
			retireStallByExLd[coreId] = count
		elif re.match(r'Ex_i', stallType):
			retireStallByExOther[coreId] += count
		else:
			print 'ERROR: unkonw retire stall type {}'.format(stallType)
			sys.exit()

for i in range(0, coreNum):
	if retireStallByVerifyLd[i] != 0 or retireStallByVerifySt[i] != 0:
		print "ERROR: core {} has retire stall by verification loads caused by Ld/St".format(i)
		sys.exit()
	if verifyLd <= 0 and (retireStallByVerifyRep[i] != 0 or retireStallByVerifyInv[i] != 0):
		print "ERROR: core {} has retire stall by verification loads caused by inv/rep".format(i)
		sys.exit()

saveData['retireStallByExLd'] = retireStallByExLd
saveData['retireStallByExOther'] = retireStallByExOther
saveData['retireStallByFlushInv'] = retireStallByFlushInv
saveData['retireStallByFlushRep'] = retireStallByFlushRep
saveData['retireStallByFlushSt'] = retireStallByFlushSt
saveData['retireStallByFlushLd'] = retireStallByFlushLd
saveData['retireStallByComSQ'] = retireStallByComSQ
saveData['retireStallByEmpty'] = retireStallByEmpty
saveData['retireStallByVerifyInv'] = retireStallByVerifyInv
saveData['retireStallByVerifyRep'] = retireStallByVerifyRep

print '-- Retire Port BW Distribution'
print '{:<6s}LdEx   OtherEx  FlushSt  FlushLd  FlushInv  FlushRep  VerifyInv  VerifyRep  ComSQ  Empty  Active'.format('(%)')
for i in range(0, coreNum):
	if cycle[i] <= 0:
		print '{:<6s}{:<7s}{:<9s}{:<9s}{:<9s}{:<10s}{:<10s}{:<11s}{:<11s}{:<7s}{:<7s}{:<8s}'.format('P({})'.format(i),
				'nan', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan')
	else:
		print '{:<6s}{:<7.2f}{:<9.2f}{:<9.3f}{:<9.3f}{:<10.3f}{:<10.3f}{:<11.3f}{:<11.3f}{:<7.2f}{:<7.2f}{:<8.2f}'.format('P({})'.format(i),
				float(retireStallByExLd[i]) / float(retireWidth) / float(cycle[i]) * 100.0,
				float(retireStallByExOther[i]) / float(retireWidth) / float(cycle[i]) * 100.0,
				float(retireStallByFlushSt[i]) / float(retireWidth) / float(cycle[i]) * 100.0,
				float(retireStallByFlushLd[i]) / float(retireWidth) / float(cycle[i]) * 100.0,
				float(retireStallByFlushInv[i]) / float(retireWidth) / float(cycle[i]) * 100.0,
				float(retireStallByFlushRep[i]) / float(retireWidth) / float(cycle[i]) * 100.0,
				float(retireStallByVerifyInv[i]) / float(retireWidth) / float(cycle[i]) * 100.0,
				float(retireStallByVerifyRep[i]) / float(retireWidth) / float(cycle[i]) * 100.0,
				float(retireStallByComSQ[i]) / float(retireWidth) / float(cycle[i]) * 100.0,
				float(retireStallByEmpty[i]) / float(retireWidth) / float(cycle[i]) * 100.0,
				100.0 - float(retireStallByExLd[i] + retireStallByExOther[i] + retireStallByFlushLd[i] 
					+ retireStallByFlushInv[i] + retireStallByFlushRep[i] + retireStallByFlushSt[i] 
					+ retireStallByVerifyInv[i] + retireStallByVerifyRep[i] + retireStallByComSQ[i]
					+ retireStallByEmpty[i]) / float(retireWidth) / float(cycle[i]) * 100.0)
print ''

# issue port stall
issueStallByOutBr = [0] * coreNum
issueStallByOutLd = [0] * coreNum
issueStallByOutSt = [0] * coreNum
issueStallByOutReg = [0] * coreNum
issueStallByOutWin = [0] * coreNum
issueStallByOutWinAunit = [0] * coreNum
issueStallByOutWinBunit = [0] * coreNum
issueStallByOutWinCunit = [0] * coreNum
issueStallByOutWinLunit = [0] * coreNum
issueStallByOutWinSunit = [0] * coreNum
issueStallByOutROB = [0] * coreNum
issueStallByReplay = [0] * coreNum
issueStallByReplayLd = [0] * coreNum
issueStallByReplaySt = [0] * coreNum
issueStallByReplayInv = [0] * coreNum
issueStallByReplayRep = [0] * coreNum
issueStallBySyscall = [0] * coreNum
issueStallByNoInst = [0] * coreNum

for line in resultFile:
	m = re.search(r'P\((\d+)\)_issueStallBy(\w+)\s*=\s*(\d+)\.0+', line)
	if m:
		coreId = int(m.group(1))
		stallType = m.group(2)
		count = int(m.group(3))
		if stallType == 'OutBr':
			issueStallByOutBr[coreId] = count
			if count != 0: # check count == 0
				print 'ERROR: issueStallByOutBr[{}] = {} != 0'.format(coreId, count)
				sys.exit()
		elif stallType == 'Syscall':
			issueStallBySyscall[coreId] = count
			if count != 0: # check count == 0
				print 'ERROR: issueStallBySyscall[{}] = {} != 0'.format(coreId, count)
				sys.exit()
		elif stallType == 'OutLd':
			issueStallByOutLd[coreId] = count
		elif stallType == 'OutSt':
			issueStallByOutSt[coreId] = count
		elif stallType == 'OutReg':
			issueStallByOutReg[coreId] = count
		elif stallType == 'OutROB':
			issueStallByOutROB[coreId] = count
		elif stallType == 'NoInst':
			issueStallByNoInst[coreId] = count
		elif stallType == 'OutWin':
			issueStallByOutWin[coreId] = count
		elif stallType == 'Replay':
			issueStallByReplay[coreId] = count
		elif stallType == 'Replay_Load':
			issueStallByReplayLd[coreId] = count
		elif stallType == 'Replay_Store':
			issueStallByReplaySt[coreId] = count
		elif stallType == 'Replay_CacheInv':
			issueStallByReplayInv[coreId] = count
		elif stallType == 'Replay_CacheRep':
			issueStallByReplayRep[coreId] = count
		else:
			print 'ERROR: unknown issue stall type {}'.format(stallType)
			sys.exit()
	else:
		m2 = re.search(r'P\((\d+)\)_([ABCLS])UNIT_issueStallByOutWin\s*=\s*(\d+)\.0+', line)
		if m2:
			coreId = int(m2.group(1))
			unit = m2.group(2)
			count = int(m2.group(3))
			if unit == 'A':
				issueStallByOutWinAunit[coreId] = count
			elif unit == 'B':
				issueStallByOutWinBunit[coreId] = count
			elif unit == 'C':
				issueStallByOutWinCunit[coreId] = count
			elif unit == 'L':
				issueStallByOutWinLunit[coreId] = count
			elif unit == 'S':
				issueStallByOutWinSunit[coreId] = count
			else:
				print 'ERROR: unkonw cluster {}'.format(unit)
				sys.exit()

for i in range(0, coreNum):
	if (issueStallByOutWinAunit[i] + issueStallByOutWinBunit[i] + issueStallByOutWinCunit[i]
			+ issueStallByOutWinLunit[i] + issueStallByOutWinSunit[i]) != issueStallByOutWin[i]:
		print 'ERROR: core {} inconsistent issueStallByOutWin'.format(i)
		sys.exit()
	if issueStallByReplayLd[i] + issueStallByReplaySt[i] + issueStallByReplayInv[i] + issueStallByReplayRep[i] != issueStallByReplay[i]:
		print 'ERROR: core {} inconsistent issueStallByReplay'.format(i)
		sys.exit()

saveData['issueStallByOutBr'] = issueStallByOutBr
saveData['issueStallByOutLd'] = issueStallByOutLd
saveData['issueStallByOutSt'] = issueStallByOutSt
saveData['issueStallByOutReg'] = issueStallByOutReg
saveData['issueStallByOutWin'] = issueStallByOutWin
saveData['issueStallByOutWinAunit'] = issueStallByOutWinAunit
saveData['issueStallByOutWinBunit'] = issueStallByOutWinBunit
saveData['issueStallByOutWinCunit'] = issueStallByOutWinCunit
saveData['issueStallByOutWinLunit'] = issueStallByOutWinLunit
saveData['issueStallByOutWinSunit'] = issueStallByOutWinSunit
saveData['issueStallByOutROB'] = issueStallByOutROB
saveData['issueStallByReplay'] = issueStallByReplay
saveData['issueStallByReplayLd'] = issueStallByReplayLd
saveData['issueStallByReplaySt'] = issueStallByReplaySt
saveData['issueStallByReplayInv'] = issueStallByReplayInv
saveData['issueStallByReplayRep'] = issueStallByReplayRep
saveData['issueStallBySyscall'] = issueStallBySyscall
saveData['issueStallByNoInst'] = issueStallByNoInst

print '-- Issue Port BW Distribution'
print '{:<6s}OutBr  OutLd  OutSt  OutReg  OutWin  OutROB  Replay  Syscall  NoInst  Active'.format('(%)')
for i in range(0, coreNum):
	if cycle[i] <= 0:
		print '{:<6s}{:<7s}{:<7s}{:<7s}{:<8s}{:<8s}{:<8s}{:<8s}{:<9s}{:<8s}{:<8s}'.format('P({})'.format(i),
				'nan', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan')
	else:
		print '{:<6s}{:<7.2f}{:<7.2f}{:<7.2f}{:<8.2f}{:<8.2f}{:<8.2f}{:<8.2f}{:<9.2f}{:<8.2f}{:<8.2f}'.format('P({})'.format(i),
				float(issueStallByOutBr[i]) / float(issueWidth) / float(cycle[i]) * 100.0,
				float(issueStallByOutLd[i]) / float(issueWidth) / float(cycle[i]) * 100.0,
				float(issueStallByOutSt[i]) / float(issueWidth) / float(cycle[i]) * 100.0,
				float(issueStallByOutReg[i]) / float(issueWidth) / float(cycle[i]) * 100.0,
				float(issueStallByOutWin[i]) / float(issueWidth) / float(cycle[i]) * 100.0,
				float(issueStallByOutROB[i]) / float(issueWidth) / float(cycle[i]) * 100.0,
				float(issueStallByReplay[i]) / float(issueWidth) / float(cycle[i]) * 100.0,
				float(issueStallBySyscall[i]) / float(issueWidth) / float(cycle[i]) * 100.0,
				float(issueStallByNoInst[i]) / float(issueWidth) / float(cycle[i]) * 100.0,
				100.0 - float(issueStallByOutBr[i] + issueStallByOutLd[i] + issueStallByOutSt[i]
					+ issueStallByOutReg[i] + issueStallByOutWin[i] + issueStallByOutROB[i]
					+ issueStallByReplay[i] + issueStallBySyscall[i] + issueStallByNoInst[i]
					) / float(issueWidth) / float(cycle[i]) * 100.0)
print ''

# rob usage
robUsage = [[0] * (robSize + 1)] * coreNum

for line in resultFile:
	m = re.search(r'P\((\d+)\)_robUsage\((\d+)\)\s*=\s*(\d+)\.0+', line)
	if m:
		robUsage[int(m.group(1))][int(m.group(2))] = int(m.group(3))

print '-- ROB Usage'
print '{:<6s}[0.0, 0.2)  [0.2, 0.4)  [0.4, 0.6)  [0.6, 0.8)  [0.8, 1.0]'.format('(%)')
for i in range(0, coreNum):
	if cycle[i] <= 0:
		print '{:<6s}{:<12s}{:<12s}{:<12s}{:<12s}{:<12s}'.format('P({})'.format(i),
				'nan', 'nan', 'nan', 'nan', 'nan')
	else:
		print '{:<6s}{:<12.2f}{:<12.2f}{:<12.2f}{:<12.2f}{:<12.2f}'.format('P({})'.format(i),
				float(sum(robUsage[i][0 : int(0.2 * robSize)])) / float(cycle[i]) * 100.0,
				float(sum(robUsage[i][int(0.2 * robSize) : int(0.4 * robSize)])) / float(cycle[i]) * 100.0,
				float(sum(robUsage[i][int(0.4 * robSize) : int(0.6 * robSize)])) / float(cycle[i]) * 100.0,
				float(sum(robUsage[i][int(0.6 * robSize) : int(0.8 * robSize)])) / float(cycle[i]) * 100.0,
				float(sum(robUsage[i][int(0.8 * robSize) :])) / float(cycle[i]) * 100.0)
print ''

# average memory latency
readMemLat = [0] * coreNum
readMemNum = [0] * coreNum
writeMemLat = [0] * coreNum
writeMemNum = [0] * coreNum
prefetchMemLat = [0] * coreNum
prefetchMemNum = [0] * coreNum

for line in resultFile:
	m = re.search(r'DL1\((\d+)\)_(\w+)MemLat:n=(\d+)::v=(\d+\.\d+)', line)
	if m:
		coreId = int(m.group(1))
		memType = m.group(2)
		num = int(m.group(3))
		lat = float(m.group(4))
		if memType == 'read':
			readMemNum[coreId] = num
			readMemLat[coreId] = lat
		elif memType == 'write':
			writeMemNum[coreId] = num
			writeMemLat[coreId] = lat
		elif memType == 'prefetch':
			prefetchMemNum[coreId] = num
			prefetchMemLat[coreId] = lat

saveData['readMemNum'] = readMemNum
saveData['readMemLat'] = readMemLat
saveData['writeMemNum'] = writeMemNum
saveData['writeMemLat'] = writeMemLat
saveData['prefetchMemNum'] = prefetchMemNum
saveData['prefetchMemLat'] = prefetchMemLat

print '-- Memory Access'
print '{:<6s}{:<16s}{:<16s}{:<16s}'.format('', 'Read', 'Write', 'Prefetch')
print ('{:<6s}' + 'ReqPKI  AvgLat  ' * 3).format('')
for i in range(0, coreNum):
	print ('{:<6s}' + '{:<8s}{:<8.1f}' * 3).format('P({})'.format(i),
			'nan' if inst[i] <= 0 else '{:<8.1f}'.format(float(readMemNum[i]) / float(inst[i]) * 1000.0), readMemLat[i],
			'nan' if inst[i] <= 0 else '{:<8.1f}'.format(float(writeMemNum[i]) / float(inst[i]) * 1000.0), writeMemLat[i],
			'nan' if inst[i] <= 0 else '{:<8.1f}'.format(float(prefetchMemNum[i]) / float(inst[i]) * 1000.0), prefetchMemLat[i])
print ''

# MSHR contention
readInsertLat = {'DL1': [0] * coreNum, 'L2': [0] * coreNum, 'L3': [0]}
writeInsertLat = {'DL1': [0] * coreNum, 'L2': [0] * coreNum, 'L3': [0]}
prefetchInsertLat = {'DL1': [0] * coreNum, 'L2': [0] * coreNum, 'L3': [0]}
readIssueLat = {'DL1': [0] * coreNum, 'L2': [0] * coreNum, 'L3': [0]}
writeIssueLat = {'DL1': [0] * coreNum, 'L2': [0] * coreNum, 'L3': [0]}
prefetchIssueLat = {'DL1': [0] * coreNum, 'L2': [0] * coreNum, 'L3': [0]}

for line in resultFile:
	m = re.search(r'(DL1|L2|L3)\((\d+)\)_MSHR_(read|write|prefetch)(Insert|Issue)Lat:n=\d+::v=(\d+\.\d+)', line)
	if m:
		cacheType = m.group(1)
		coreId = int(m.group(2))
		reqType = m.group(3)
		action = m.group(4)
		lat = float(m.group(5))
		if action == 'Insert':
			if reqType == 'read':
				readInsertLat[cacheType][coreId] = lat
			elif reqType == 'write':
				writeInsertLat[cacheType][coreId] = lat
			elif reqType == 'prefetch':
				prefetchInsertLat[cacheType][coreId] = lat
			else:
				print 'ERROR: unknown req type {}'.format(reqType)
				sys.exit()
		elif action == 'Issue':
			if reqType == 'read':
				readIssueLat[cacheType][coreId] = lat
			elif reqType == 'write':
				writeIssueLat[cacheType][coreId] = lat
			elif reqType == 'prefetch':
				prefetchIssueLat[cacheType][coreId] = lat
			else:
				print 'ERROR: unknown req type {}'.format(reqType)
				sys.exit()
		else:
			print 'ERROR: unknown action {}'.format(action)
			sys.exit()

for cache in ['DL1', 'L2', 'L3']:
	saveData['readInsertLat{}'.format(cache)] = readInsertLat[cache]
	saveData['readIssueLat{}'.format(cache)] = readIssueLat[cache]
	saveData['writeInsertLat{}'.format(cache)] = writeInsertLat[cache]
	saveData['writeIssueLat{}'.format(cache)] = writeIssueLat[cache]
	saveData['prefetchInsertLat{}'.format(cache)] = prefetchInsertLat[cache]
	saveData['prefetchIssueLat{}'.format(cache)] = prefetchIssueLat[cache]

print '-- Memory Access Latency Distribution'
print ('{:<6s}' + '{:<23s}' * 3).format('', 'Read', 'Write', 'Prefetch')
print ('{:<6s}' + 'Insert  Issue  Handle  ' * 3).format('')
for i in range(0, coreNum):
	print ('{:<6s}' + '{:<8.1f}{:<7.1f}{:<8.1f}' * 3).format('P({})'.format(i),
			readInsertLat['DL1'][i], readIssueLat['DL1'][i], readMemLat[i] - readInsertLat['DL1'][i] - readIssueLat['DL1'][i],
			writeInsertLat['DL1'][i], writeIssueLat['DL1'][i], writeMemLat[i] - writeInsertLat['DL1'][i] - writeIssueLat['DL1'][i],
			prefetchInsertLat['DL1'][i], prefetchIssueLat['DL1'][i], prefetchMemLat[i] - prefetchInsertLat['DL1'][i] - prefetchIssueLat['DL1'][i])
print ''

# cache miss
readMissNum = {'DL1': [0] * coreNum, 'L2': [0] * coreNum, 'L3': [0]}
readMissLat = {'DL1': [0] * coreNum, 'L2': [0] * coreNum, 'L3': [0]}
writeMissNum = {'DL1': [0] * coreNum, 'L2': [0] * coreNum, 'L3': [0]}
writeMissLat = {'DL1': [0] * coreNum, 'L2': [0] * coreNum, 'L3': [0]}
prefetchMissNum = {'DL1': [0] * coreNum, 'L2': [0] * coreNum, 'L3': [0]}
prefetchMissLat = {'DL1': [0] * coreNum, 'L2': [0] * coreNum, 'L3': [0]}

for line in resultFile:
	m = re.search(r'(DL1|L2|L3)\((\d+)\)_MSHR_(read|write|prefetch)MissLat:n=(\d+)::v=(\d+\.\d+)', line)
	if m:
		cacheType = m.group(1)
		coreId = int(m.group(2))
		missType = m.group(3)
		num = int(m.group(4))
		lat = float(m.group(5))
		if missType == 'read':
			readMissNum[cacheType][coreId] = num
			readMissLat[cacheType][coreId] = lat
		elif missType == 'write':
			writeMissNum[cacheType][coreId] = num
			writeMissLat[cacheType][coreId] = lat
		elif missType == 'prefetch':
			prefetchMissNum[cacheType][coreId] = num
			prefetchMissLat[cacheType][coreId] = lat
		else:
			print 'ERROR: unknown miss type {}'.format(missType)
			sys.exit()

for cache in ['DL1', 'L2', 'L3']:
	saveData['readMissNum{}'.format(cache)] = readMissNum[cache]
	saveData['readMissLat{}'.format(cache)] = readMissLat[cache]
	saveData['writeMissNum{}'.format(cache)] = writeMissNum[cache]
	saveData['writeMissLat{}'.format(cache)] = writeMissLat[cache]
	saveData['prefetchMissNum{}'.format(cache)] = prefetchMissNum[cache]
	saveData['prefetchMissLat{}'.format(cache)] = prefetchMissLat[cache]

print '-- Cache Miss'
print '{:<8s}{:<14s}{:<14s}{:<14s}'.format('', 'Read', 'Write', 'Prefetch')
print ('{:<8s}' + 'MPKI  AvgLat  ' * 3).format('')
for cache in ['DL1', 'L2', 'L3']:
	for i in range(0, 1 if cache == 'L3' else coreNum):
		instNum = float(sum(inst) if cache == 'L3' else inst[i])
		print ('{:8s}' + '{:<6s}{:<8.1f}' * 3).format('{}({})'.format(cache, i),
				'nan' if instNum <= 0 else '{:<6.1f}'.format(float(readMissNum[cache][i]) / instNum * 1000.0), readMissLat[cache][i],
				'nan' if instNum <= 0 else '{:<6.1f}'.format(float(writeMissNum[cache][i]) / instNum * 1000.0), writeMissLat[cache][i],
				'nan' if instNum <= 0 else '{:<6.1f}'.format(float(prefetchMissNum[cache][i]) / instNum * 1000.0), prefetchMissLat[cache][i])
print ''

# LSQ
excepByRep = [0] * coreNum
excepByInv = [0] * coreNum
excepByLd = [0] * coreNum
excepBySt = [0] * coreNum
ldVioByRep = [0] * coreNum # violation is LdKillBy
ldVioByInv = [0] * coreNum
ldVioByLd = [0] * coreNum
ldVioBySt = [0] * coreNum
ldReExByRep = [0] * coreNum
ldReExByInv = [0] * coreNum
ldReExByLd = [0] * coreNum
ldReExBySt = [0] * coreNum
ldStallByLd = [0] * coreNum
ldStallByRec = [0] * coreNum
verifyLdByInv = [0] * coreNum
verifyLdByRep = [0] * coreNum
stForward = [0] * coreNum
ldForward = [0] * coreNum
exLdHist = [[0] * (maxLd + 1)] * coreNum
doneLdHist = [[0] * (maxLd + 1)] * coreNum
ldQUsage = [[0] * (maxLd + 1)] * coreNum
stQUsage = [[0] * (maxSt + 1)] * coreNum
comSQUsage = [[0] * (maxSt + 1)] * coreNum

for line in resultFile:
	m = re.search(r'P\((\d+)\)_MTLSQ_n(\w+)\s*=\s*(\d+)\.0+', line)
	if m:
		coreId = int(m.group(1))
		cntType = m.group(2)
		count = int(m.group(3))
		if cntType == 'LdKillByRep':
			ldVioByRep[coreId] = count
		elif cntType == 'LdKillByInv':
			ldVioByInv[coreId] = count
		elif cntType == 'LdKillByLd':
			ldVioByLd[coreId] = count
		elif cntType == 'LdKillBySt':
			ldVioBySt[coreId] = count
		elif cntType == 'LdReExByRep':
			ldReExByRep[coreId] = count
		elif cntType == 'LdReExByInv':
			ldReExByInv[coreId] = count
		elif cntType == 'LdReExByLd':
			ldReExByLd[coreId] = count
		elif cntType == 'LdReExBySt':
			ldReExBySt[coreId] = count
		elif cntType == 'LdStallByLd':
			ldStallByLd[coreId] = count
		elif cntType == 'LdStallByRec':
			ldStallByRec[coreId] = count
		elif cntType == 'VerifyLdByRep':
			verifyLdByRep[coreId] = count
		elif cntType == 'VerifyLdByInv':
			verifyLdByInv[coreId] = count
		elif cntType == 'VerifyByLd' or cntType == 'VerifyBySt':
			if count != 0:
				print 'ERROR: {} > 0'.format(line)
				sys.exit()
		elif cntType == 'LdLdForward':
			ldForward[coreId] = count
		elif cntType == 'StLdForward':
			stForward[coreId] = count
		elif cntType != 'UnalignLd' and cntType != 'UnalignSt':
			print 'ERROR: unkown count type {}'.format(cntType)
			sys.exit()
		continue
	m = re.search(r'P\((\d+)\)_nExcepBy_(\w+)\s*=\s*(\d+)\.0+', line)
	if m:
		coreId = int(m.group(1))
		excepType = m.group(2)
		count = int(m.group(3))
		if excepType == 'CacheRep':
			excepByRep[coreId] = count
		elif excepType == 'CacheInv':
			excepByInv[coreId] = count
		elif excepType == 'Load':
			excepByLd[coreId] = count
		elif excepType == 'Store':
			excepBySt[coreId] = count
		else:
			print 'ERROR: unkown exception type {}'.format(excepType)
			sys.exit()
		continue
	m = re.search(r'P\((\d+)\)_(ldQUsage|exLdNum|doneLdNum|stQUsage|comSQUsage)\((\d+)\)\s*=\s*(\d+)\.0+', line)
	if m:
		coreId = int(m.group(1))
		histType = m.group(2)
		key = int(m.group(3))
		val = int(m.group(4))
		if histType == 'ldQUsage':
			ldQUsage[coreId][key] = val
		elif histType == 'exLdNum':
			exLdHist[coreId][key] = val
		elif histType == 'doneLdNum':
			doneLdHist[coreId][key] = val
		elif histType == 'stQUsage':
			stQUsage[coreId][key] = val
		elif histType == 'comSQUsage':
			comSQUsage[coreId][key] = val
		else:
			print 'ERROR: unkown LSQ hist type {}'.format(histType)
			sys.exit()

saveData['excepByRep'] = excepByRep
saveData['excepByInv'] = excepByInv
saveData['excepByLd'] = excepByLd
saveData['excepBySt'] = excepBySt
saveData['ldVioByRep'] = ldVioByRep
saveData['ldVioByInv'] = ldVioByInv
saveData['ldVioByLd'] = ldVioByLd
saveData['ldVioBySt'] = ldVioBySt
saveData['ldReExByRep'] = ldReExByRep
saveData['ldReExByInv'] = ldReExByInv
saveData['ldReExByLd'] = ldReExByLd
saveData['ldReExBySt'] = ldReExBySt
saveData['ldStallByLd'] = ldStallByLd
saveData['ldStallByRec'] = ldStallByRec
saveData['verifyLdByRep'] = verifyLdByRep
saveData['verifyLdByInv'] = verifyLdByInv
saveData['ldForward'] = ldForward
saveData['stForward'] = stForward
saveData['exLdHist'] = exLdHist
saveData['doneLdHist'] = doneLdHist
saveData['ldQUsage'] = ldQUsage
saveData['stQUsage'] = stQUsage
saveData['comSQUsage'] = comSQUsage

# save data to .mat & .json files
if len(sys.argv) >= 3:
	if not os.path.isdir(sys.argv[2]):
		print 'ERROR: cannot file {}'.format(sys.argv[2])
		sys.exit()

	fileName = os.path.basename(sys.argv[1]).split('.')[0]
	jsonName = os.path.join(sys.argv[2], fileName + '.json')
	matName = os.path.join(sys.argv[2], fileName + '.mat')
	if os.path.isfile(jsonName) or os.path.isfile(matName):
		print 'ERROR: {} or {} already exists'.format(jsonName, matName)
		sys.exit()

	sio.savemat(matName, mdict = saveData, appendmat = False, oned_as = 'column')

	fp = open(jsonName, 'w')
	json.dump(saveData, fp)
	fp.close()
