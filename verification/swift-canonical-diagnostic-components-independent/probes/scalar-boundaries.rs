#![forbid(unsafe_code)]
fn write_words(output: &mut [u8], words: &[u64]) {
    for (slot, word) in output.as_chunks_mut::<8>().0.iter_mut().zip(words) {
        slot.copy_from_slice(&word.to_le_bytes());
    }
}

#[test]
fn actual_helper_unaligned_lengths_word_counts_and_tails() {
    let mut lengths: Vec<usize> = (0..=145).collect();
    lengths.extend([255,256,257,511,512,513,1023,1024,1025,2047,2048,2049]);
    let mut counts: Vec<usize> = (0..=20).collect();
    counts.extend([63,64,65,255,256,257]);
    let mut cases = 0u64;
    let mut checked_bytes = 0u64;
    let mut unaligned_cases = 0u64;
    let mut tail_cases = 0u64;
    let mut fewer_words_cases = 0u64;
    let mut excess_words_cases = 0u64;
    for length in lengths {
        for &count in &counts {
            let words: Vec<u64> = (0..count).map(|n| match n % 8 {
                0 => 0,
                1 => u64::MAX,
                2 => 0x0123_4567_89ab_cdef,
                3 => 0x8000_0000_0000_0001,
                4 => 1u64 << (n % 64),
                5 => 0x00ff_aa55_f00f_3399,
                _ => (n as u64).wrapping_mul(0x9e37_79b9_7f4a_7c15).rotate_left((n % 64) as u32),
            }).collect();
            for offset in 0..16 {
                let size = offset + length + 17;
                let before: Vec<u8> = (0..size).map(|n| (n as u8).wrapping_mul(37).wrapping_add(0x5b)).collect();
                let mut actual = before.clone();
                write_words(&mut actual[offset..offset + length], &words);
                // Independent byte oracle: index and shift scalar words. It
                // uses neither byte-conversion methods nor chunk iteration.
                let written = std::cmp::min(length / 8,count) * 8;
                for index in 0..size {
                    let want = if index >= offset && index - offset < written {
                        let relative = index - offset;
                        ((words[relative / 8] >> (8 * (relative % 8))) & 255) as u8
                    } else {
                        before[index]
                    };
                    assert_eq!(actual[index],want,"length={length} words={count} offset={offset} byte={index}");
                }
                cases += 1;
                checked_bytes += size as u64;
                unaligned_cases += u64::from(actual[offset..].as_ptr().align_offset(8) != 0);
                tail_cases += u64::from(length % 8 != 0);
                fewer_words_cases += u64::from(count < length / 8);
                excess_words_cases += u64::from(count > length / 8);
            }
        }
    }
    assert_eq!(cases, 68_256);
    assert!(unaligned_cases > 0 && tail_cases > 0 && fewer_words_cases > 0 && excess_words_cases > 0);
    println!("BOUNDARIES cases={cases} checked_bytes={checked_bytes} unaligned_cases={unaligned_cases} tail_cases={tail_cases} fewer_words_cases={fewer_words_cases} excess_words_cases={excess_words_cases}");
}
