"""Small independent BSD ar / Mach-O reader for evidence custody, not a loader."""
import struct

def archive_members(data):
    assert data[:8]==b'!<arch>\n'
    out=[];pos=8
    while pos<len(data):
        h=data[pos:pos+60];assert len(h)==60 and h[58:60]==b'`\n'
        length=int(h[48:58]);start=pos+60;body=data[start:start+length];assert len(body)==length
        name=h[:16].decode().strip()
        if name.startswith('#1/'):
            k=int(name[3:]);assert 0<=k<=length
            name=body[:k].rstrip(b'\0').decode();start+=k;body=body[k:]
        else: name=name.rstrip('/')
        out.append(dict(name=name,offset=start,data=body))
        pos+=60+length+(length%2)
    assert pos==len(data)
    return out

def macho(data):
    header=struct.unpack_from('<8I',data)
    assert header[0]==0xfeedfacf and header[1]==0x100000c and header[3]==1
    pos=32;sections=[];symtab=None
    for _ in range(header[4]):
        cmd,size=struct.unpack_from('<II',data,pos);assert size>=8 and pos+size<=32+header[5]
        if cmd==0x19:
            vals=struct.unpack_from('<II16sQQQQiiII',data,pos)
            for i in range(vals[-2]):
                s=struct.unpack_from('<16s16sQQIIIIIIII',data,pos+72+i*80)
                section=dict(name=s[0].rstrip(b'\0').decode(),segment=s[1].rstrip(b'\0').decode(),address=s[2],size=s[3],offset=s[4],alignment_power=s[5],relocation_offset=s[6],relocation_count=s[7],flags=s[8],index=len(sections)+1)
                if s[4]: assert s[4]+s[3]<=len(data)
                sections.append(section)
        if cmd==2: symtab=struct.unpack_from('<6I',data,pos)
        pos+=size
    assert pos==32+header[5] and symtab
    _,_,off,count,stroff,strsize=symtab;assert off+16*count<=len(data) and stroff+strsize<=len(data)
    strings=data[stroff:stroff+strsize];symbols=[]
    for i in range(count):
        si,typ,section,desc,value=struct.unpack_from('<IBBHQ',data,off+i*16)
        assert si<len(strings);end=strings.index(0,si)
        symbols.append(dict(index=i,name=strings[si:end].decode(),type=typ,section=section,description=desc,value=value))
    relocations=[]
    for section in sections:
        off=section['relocation_offset'];count=section['relocation_count'];assert off+8*count<=len(data)
        for i in range(count):
            address,word=struct.unpack_from('<iI',data,off+8*i)
            assert address>=0
            external=bool((word>>27)&1);index=word&0xffffff
            if word>>28==10:
                assert not external
                target='addend:'+str(index if index<0x800000 else index-0x1000000)
            elif external: target=symbols[index]['name']
            elif index==0: target='absolute'
            else: target=sections[index-1]['name']
            relocations.append(dict(section=section['index'],address=address,pc_relative=bool((word>>24)&1),width_power=(word>>25)&3,external=external,type=word>>28,target=target,record_offset=off+8*i))
    return dict(header=list(header),sections=sections,symbols=symbols,relocations=relocations)

def at_address(data,parsed,address,size):
    matches=[s for s in parsed['sections'] if s['offset'] and s['address']<=address and address+size<=s['address']+s['size']]
    assert len(matches)==1
    s=matches[0];off=s['offset']+address-s['address']
    return data[off:off+size],off,s
