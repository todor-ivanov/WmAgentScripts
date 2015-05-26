#!/usr/bin/env python
from assignSession import *
from McMClient import McMClient
from utils import workflowInfo
import reqMgrClient
import setDatasetStatusDBS3
from utils import componentInfo

def invalidator(url, invalid_status='INVALID'):
    up = componentInfo(mcm=True)
    mcm = McMClient(dev=False)
    invalids = mcm.getA('invalidations',query='status=announced')
    print len(invalids),"Object to be invalidated"
    text_to_batch = defaultdict(str)
    for invalid in invalids:
        acknowledge= False
        pid = invalid['prepid']
        text = ""
        if invalid['type'] == 'request':
            wfn = invalid['object']
            print "need to invalidate the workflow",wfn
            wfo = session.query(Workflow).filter(Workflow.name == wfn).first()
            if wfo:
                ## set forget of that thing (although checkor will recover from it)
                wfo.status = 'forget'
                session.commit()
            else:
                ## do not go on like this, do not acknoledge it
                print wfn,"is set to be rejected, but we do not know about it yet"
                continue
            wfi = workflowInfo(url, wfn)
            success = "not rejected"
            if wfi.request['RequestStatus'] in ['assignment-approved','new','completed']:
                success = reqMgrClient.rejectWorkflow(url, wfn)
                pass
            else:
                success = reqMgrClient.abortWorkflow(url, wfn)
                pass
            print success
            acknowledge= True
            text = "The workflow %s (%s) was rejected due to invalidation in McM" % ( wfn, pid )
        elif invalid['type'] == 'dataset':
            dataset = invalid['object']

            if '?' in dataset: continue
            if 'None' in dataset: continue
            if 'None-' in dataset: continue
            if 'FAKE-' in dataset: continue

            print "setting",dataset,"to",invalid_status
            success = "not invalidated"
            success = setDatasetStatusDBS3.setStatusDBS3('https://cmsweb.cern.ch/dbs/prod/global/DBSWriter', dataset, invalid_status, None)
            print success
            ## make a delete request from everywhere we can find ?
            acknowledge= True
            text = "The dataset %s (%s) was set INVALID due to invalidation in McM" % ( dataset, pid )
        else:
            print "\t\t",invalid['type']," type not recognized"

        if acknowledge:
            ## acknoldge invalidation in mcm, provided we can have the api
            print "acknowledgment to mcm"
            mcm.get('/restapi/invalidations/acknowledge/%s'%( invalid['_id'] ))
            batches = mcm.getA('batches',query='contains=%s'%pid)
            if len(batches):
                bid = batches[-1]['prepid']
                print "batch nofication to",bid
                text_to_batch[bid] += text+"\n"

    for bid,text in text_to_batch.items():    
        mcm.put('/restapi/batches/notify',{ "notes" : text, "prepid" : bid})
        pass


if __name__ == "__main__":
    url = 'cmsweb.cern.ch'
    invalidator(url)
