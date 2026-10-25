"""Closed validation of actual bridge/Settings outputs; auxiliary bytes grant no app authority.

The unchanged Session validates and reconstructs each journal-linked publication
in memory. The unchanged TransactionStore's successful hard-link publication and
retirement receipts must account for every retained attempt and payload.
"""
import os
from pathlib import Path
import stat
import uuid
import importer as i
import reference_contract as contract
import settings_telemetry as telemetry

APP_FILES = {'0001-begin.json','0001-ready.json','0001-command-1.json','0001-command-2.json','0001-before-1.json','0001-after-1.json','0001-keyboard-witness-1.json','0001-focus-diagnostic-1.json'}
ROLES = {'begin':'0001-begin.json','before':'0001-before-1.json','after':'0001-after-1.json','witness':'0001-keyboard-witness-1.json'}


def regular(path, limit=2_000_000, links=None):
    info=path.lstat()
    i.require(path.resolve()==path and stat.S_ISREG(info.st_mode) and 0<info.st_size<=limit and (links is None or info.st_nlink==links),'Auxiliary path/type/size/link count changed: '+path.name)
    return path.read_bytes()


def directory(path):
    info=path.lstat()
    i.require(path.resolve()==path and stat.S_ISDIR(info.st_mode) and not path.is_symlink(),'Auxiliary directory redirected: '+path.name)


def bridge_summary(folder, app):
    value=i.parse(regular(folder/'bridge-summary.json',links=1))
    i.require(type(value) is dict and set(value)=={'generation','currentCase','allowedCases','verdicts','failures','lastValidObservationAvailable','capabilityRetained'},'Closed bridge summary required')
    i.require(type(value['generation']) is int and value['generation'] in (0,1) and value['currentCase']==(None if value['generation']==0 else i.CASE),'Bridge summary generation/case differs')
    i.require(value['allowedCases']==[i.CASE] and value['failures']==[] and value['capabilityRetained'] is False and type(value['lastValidObservationAvailable']) is bool,'Bridge summary failure/uncertainty/scope rejected')
    i.require(type(value['verdicts']) is list and len(value['verdicts'])<=1,'Bridge summary duplicate verdict rejected')
    if value['generation']==0:
        i.require(not app and value['verdicts']==[] and value['lastValidObservationAvailable'] is False,'Bridge summary conceals application generation')
    else:
        i.require('0001-begin.json' in app,'Bridge summary generation lacks application begin')
        if '0001-after-1.json' in app:
            after=i.parse(app['0001-after-1.json'])
            i.require(contract.strict_json_equal(value['verdicts'],[after.get('verdict')]),'Auxiliary summary differs from retained app verdict')
        else:i.require(value['verdicts']==[],'Auxiliary verdict lacks authoritative application after sample')
    return value


def validate(folder, identity):
    directory(folder)
    entries={path.name:path for path in folder.iterdir()}
    i.require(len(entries)<=6000 and 'bridge-summary.json' in entries,'Bounded actual bridge summary inventory required')
    i.require('.settings-transaction-guard.json' not in entries,'Unresolved Settings transaction guard rejects capture')
    app={name:regular(path,limit=16_000_000,links=1) for name,path in entries.items() if name in APP_FILES}
    summary=bridge_summary(folder,app)
    journal_names=sorted(name for name in entries if name.startswith('0000-settings-'))
    i.require(len(journal_names)<=telemetry.MAX_REQUESTS,'Settings journal count exceeds unchanged request cap')
    i.require(journal_names==[f'0000-settings-{n:04d}.json' for n in range(len(journal_names))],'Settings journal sequence/name differs')
    expected_payloads={};per_journal={};journals={}
    if journal_names:
        first=i.parse(regular(folder/journal_names[0],links=2))
        i.require(type(first) is dict and set(first)=={'receivedUptime','generation','sessionDeadlineUptime','diagnosticDeadlineUptime','record','ownedSimulatorIdentity'},'Closed first Settings journal required')
        i.require(type(first['generation']) is str and str(uuid.UUID(first['generation']))==first['generation'],'Canonical Settings session generation required')
        i.require(contract.strict_json_equal(first['ownedSimulatorIdentity'],identity),'Settings journal belongs to another owned device')
        clock=[first['receivedUptime']];generated=[];active=[None]
        def persist(suffix,value):
            i.require('0000-'+suffix+'.json'==active[0],'Settings replay suffix differs')
            generated.append({**value,'ownedSimulatorIdentity':identity})
        def publish(slot,form,payload):
            name=slot+('.png' if form=='png' else '.txt')
            i.require(name not in expected_payloads and Path(name).name==name,'Duplicate/redirected journal-linked Settings payload')
            expected_payloads[name]=payload;per_journal[active[0]].append(name)
            i.require(regular(folder/name,limit=2_000_000,links=2)==payload,'Settings payload differs from Session-reconstructed bytes')
        session=telemetry.Session(persist,publish,first['sessionDeadlineUptime'],now=lambda:clock[0],token=first['generation'])
        for index,name in enumerate(journal_names):
            saved=i.parse(regular(folder/name,links=2));journals[name]=saved;active[0]=name;per_journal[name]=[]
            expected={'receivedUptime','record','ownedSimulatorIdentity'} | ({'generation','sessionDeadlineUptime','diagnosticDeadlineUptime'} if index==0 else set())
            i.require(type(saved) is dict and set(saved)==expected and type(saved['record']) is dict and contract.strict_json_equal(saved['ownedSimulatorIdentity'],identity),'Closed Session journal/identity required')
            i.require(i.number(saved['receivedUptime']),'Settings receipt time malformed')
            clock[0]=saved['receivedUptime'];session.request(saved['record'])
            i.require(len(generated)==index+1 and contract.strict_json_equal(generated[-1],saved),'Settings journal differs from complete unchanged Session replay')
        replay=session.summary()
    else:
        replay=None
    attempts=folder/'.settings-attempts'
    if journal_names:
        i.require(attempts.name in entries,'Settings journal lacks retained transaction attempts')
        directory(attempts);children=list(attempts.iterdir())
        i.require(len(children)==len(journal_names),'Settings attempts/journals are not one-to-one')
        accounted=set()
        for attempt in children:
            directory(attempt)
            i.require(str(uuid.UUID(attempt.name))==attempt.name,'Noncanonical Settings attempt identity')
            outcome=i.parse(regular(attempt/'outcome.json',links=1))
            i.require(type(outcome) is dict and set(outcome)=={'ancillary','commitPoint','journal','outcome','retirement'} and outcome['ancillary']==[] and outcome['outcome']=='committed' and outcome['commitPoint']=='successful-evidence-exact-publication-and-publication-directory-fsync','Settings failed/ancillary/unresolved attempt rejected')
            i.require(contract.strict_json_equal(outcome['retirement'],{'state':'resolved','guardAbsenceEstablished':True,'directoryFsyncSucceeded':True,'committedRequestUnchanged':True}),'Settings guard retirement unobserved/uncertain')
            journal=outcome['journal']
            i.require(type(journal) is str and journal in journals and journal not in accounted,'Foreign/duplicate Settings attempt journal')
            accounted.add(journal)
            expected={journal,*per_journal[journal]}
            i.require({p.name for p in attempt.iterdir()}==expected|{'outcome.json'},'Unexpected/unreferenced staged Settings publication')
            for name in expected:
                staged,final=attempt/name,folder/name
                raw=regular(staged,limit=2_000_000,links=2)
                i.require(raw==regular(final,limit=2_000_000,links=2) and os.path.samefile(staged,final),'Staged Settings publication identity/bytes differ')
        i.require(accounted==set(journal_names),'Missing Settings transaction outcome')
    else:
        i.require(attempts.name not in entries,'Settings attempts without valid Session journals rejected')
    allowed=APP_FILES|{'bridge-summary.json'}|set(journal_names)|set(expected_payloads)|({'.settings-attempts'} if journal_names else set())
    i.require(set(entries)<=allowed,'Unrecognized/failure/foreign generation/action Settings or app artifact')
    # Auxiliary data cannot supply any of these roles. Return only the four fixed
    # application files; native import still needs selected official attachments.
    return {role:app[name] for role,name in ROLES.items() if name in app}, {'schema':'mixer.apple-focus-reference-auxiliary-inventory.3','bridgeSummaryGeneration':summary['generation'],'settingsJournalCount':len(journal_names),'settingsPayloadCount':len(expected_payloads),'settingsAttemptCount':len(journal_names),'settingsReplay':replay,'authoritativeApplicationEvidenceCreated':False}
