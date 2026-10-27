//! Fixed test-only host dispatcher; no pointer, owner or callback crosses this seam.
#[cfg(mixer_initial_profile_component_host)]
#[no_mangle]
pub extern "C" fn mixer_initial_profile_component_host_v1(method:u32)->u32 {
 match method {
  1=>super::tests::selected_layout_and_places(),
  2=>super::tests::fresh_header_rows_and_cleanup(),
  3=>super::tests::same_control_wasi_and_unrelated_owners(),
  4=>super::tests::complete17_drift_precedes_prepare(),
  5=>super::tests::explicit_narrowed_budgets(),
  6=>super::tests::header_retained_when_actual_row_file_refuses(),
  7=>super::tests::all64_slot_pin_pairs_checked(),
  8=>super::tests::local_structure_refusals(),
  _=>return 64,
 }
 0
}
