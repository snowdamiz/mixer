%% Official installed module: Mix.Tasks.Test
%% BEAM: /opt/homebrew/Cellar/elixir/1.20.4/lib/elixir/bin/../lib/mix/ebin/Elixir.Mix.Tasks.Test.beam
%% BEAM SHA-256: db18f3d441dbcb9d45baea325eab8908bbcf678d5d135ba4a72388822e70b4a7
%% Compile information: [version: ~c"10.0.3", options: [:no_spawn_compiler_process, :from_core, :no_core_prepare, :no_auto_import, {:no_warn_undefined, [IEx, ExUnit, ExUnit.Filters]}], source: ~c"/private/tmp/elixir-20260828-4709-q6w1ex/elixir-1.20.4/lib/mix/lib/mix/tasks/test.ex"]

abort_due_to_warnings(_shell@1, _opts@1) ->
    case 'Elixir.Access':get(_opts@1, raise) of
        _1
            when
                _1 =:= false
                orelse
                _1 =:= nil ->
            _message@1 =
                <<"\nERROR! Test suite aborted after successful executi"
                  "on due to warnings while using the --warnings-as-err"
                  "ors option">>,
            'Elixir.IO':puts(stderr,
                             'Elixir.IO.ANSI':format([red, _message@1])),
            'Elixir.System':at_exit(fun(_) ->
                                           exit({shutdown, 1})
                                    end);
        _ ->
            _message@2 =
                <<"test suite aborted after successful execution due to"
                  " warnings while using the --warnings-as-errors optio"
                  "n">>,
            raise_with_shell(_shell@1, _message@2)
    end.
'any_file_matches?'(_file@1, _filters@1) ->
    'Elixir.Enum':'any?'(_filters@1,
                         fun(_filter@1) ->
                                case _filter@1 of
                                    _regex@1
                                        when
                                            ((is_map(_regex@1)
                                              andalso
                                              (is_atom('Elixir.Regex')
                                               orelse
                                               fail))
                                             andalso
                                             is_map_key('__struct__',
                                                        _regex@1))
                                            andalso
                                            map_get('__struct__',
                                                    _regex@1)
                                            ==
                                            'Elixir.Regex' ->
                                        'Elixir.Regex':'match?'(_regex@1,
                                                                _file@1);
                                    _binary@1 when is_binary(_binary@1) ->
                                        _file@1 == _binary@1;
                                    _fun@1 when is_function(_fun@1, 1) ->
                                        _fun@1(_file@1)
                                end
                         end).
classify_test_files(_shell@1, _potential_test_files@1, _project@1) ->
    _test_load_filters@1 =
        case 'Elixir.Access':get(_project@1, test_load_filters) of
            _1
                when
                    _1 =:= false
                    orelse
                    _1 =:= nil ->
                [fun(_2) ->
                        'Elixir.String':'ends_with?'(_2,
                                                     <<"_test.exs">>)
                 end];
            _3 ->
                _3
        end,
    _test_ignore_filters@1 =
        get_test_ignore_filters(_shell@1, _project@1),
    {_to_load@2, _to_ignore@2, _to_warn@2} =
        'Elixir.Enum':reduce(_potential_test_files@1,
                             {[], [], []},
                             fun(_file@1, _6) ->
                                    case _6 of
                                        {_to_load@1, _to_ignore@1,
                                         _to_warn@1} ->
                                            case
                                                'any_file_matches?'(_file@1,
                                                                    _test_load_filters@1)
                                            of
                                                _5
                                                    when
                                                        _5 /= nil
                                                        andalso
                                                        _5 /= false ->
                                                    {[_file@1 |
                                                      _to_load@1],
                                                     _to_ignore@1,
                                                     _to_warn@1};
                                                _ ->
                                                    case
                                                        'any_file_matches?'(_file@1,
                                                                            _test_ignore_filters@1)
                                                    of
                                                        _4
                                                            when
                                                                _4
                                                                /=
                                                                nil
                                                                andalso
                                                                _4
                                                                /=
                                                                false ->
                                                            {_to_load@1,
                                                             [_file@1 |
                                                              _to_ignore@1],
                                                             _to_warn@1};
                                                        _ ->
                                                            case true of
                                                                true ->
                                                                    {_to_load@1,
                                                                     _to_ignore@1,
                                                                     [_file@1 |
                                                                      _to_warn@1]};
                                                                false ->
                                                                    error(cond_clause)
                                                            end
                                                    end
                                            end
                                    end
                             end),
    {'Elixir.Enum':reverse(_to_load@2),
     'Elixir.Enum':reverse(_to_ignore@2),
     'Elixir.Enum':reverse(_to_warn@2)}.
do_run(_opts@1, _args@1, _files@1) ->
    _ = 'Elixir.Mix.Project':'get!'(),
    case
        case 'Elixir.System':get_env(<<"MIX_ENV">>) == nil of
            _1
                when
                    _1 =:= false
                    orelse
                    _1 =:= nil ->
                _1;
            _ ->
                'Elixir.Mix':env() /= test
        end
    of
        _2
            when
                _2 =:= false
                orelse
                _2 =:= nil ->
            nil;
        _ ->
            'Elixir.Mix':raise(<<"\"mix test\" is running in the \"",
                                 case 'Elixir.Mix':env() of
                                     _3 when is_binary(_3) ->
                                         _3;
                                     _3 ->
                                         'Elixir.String.Chars':to_string(_3)
                                 end/binary,
                                 "\" environment. If you are running te"
                                 "sts from within another command, you "
                                 "can either:\n\n  1. set MIX_ENV expli"
                                 "citly:\n\n      MIX_ENV=test mix test"
                                 ".another\n\n  2. set the :preferred_e"
                                 "nvs for \"def cli\" in your mix.exs:"
                                 "\n\n      def cli do\n        [prefer"
                                 "red_envs: [\"test.another\": :test]]"
                                 "\n      end\n">>)
    end,
    case 'Elixir.Access':get(_opts@1, listen_on_stdin) of
        _4
            when
                _4 =:= false
                orelse
                _4 =:= nil ->
            nil;
        _ ->
            'Elixir.System':at_exit(fun(_) ->
                                           'Elixir.IO':gets(stdio, <<>>),
                                           ('Elixir.Mix':shell()):info(<<"Resta"
                                                                         "rting"
                                                                         "...">>),
                                           'Elixir.System':restart(),
                                           'Elixir.Process':sleep(infinity)
                                    end)
    end,
    'Elixir.Application':ensure_loaded(ex_unit),
    'Elixir.Mix.Task':run(<<"compile">>,
                          erlang:'--'(_args@1,
                                      [<<"--warnings-as-errors">>])),
    _project@1 = 'Elixir.Mix.Project':config(),
    {_partitions@1, _opts@2} = 'Elixir.Keyword':pop(_opts@1, partitions),
    _partitioned?@1 =
        case is_integer(_partitions@1) of
            false ->
                false;
            true ->
                _partitions@1 > 1
        end,
    _cover@2 =
        case 'Elixir.Access':get(_opts@2, cover) of
            _5
                when
                    _5 =:= false
                    orelse
                    _5 =:= nil ->
                nil;
            _ ->
                _compile_path@1 =
                    'Elixir.Mix.Project':compile_path(_project@1),
                _partition@1 =
                    case _partitioned?@1 of
                        _6
                            when
                                _6 =:= false
                                orelse
                                _6 =:= nil ->
                            _6;
                        _ ->
                            'Elixir.System':get_env(<<"MIX_TEST_PARTITI"
                                                      "ON">>)
                    end,
                _cover@1 =
                    'Elixir.Keyword':merge('Elixir.Keyword':put([{output,
                                                                  <<"cover">>},
                                                                 {tool,
                                                                  'Elixir.Mix.Tasks.Test.Coverage'}],
                                                                export,
                                                                case
                                                                    'Elixir.Access':get(_opts@2,
                                                                                        export_coverage)
                                                                of
                                                                    _7
                                                                        when
                                                                            _7
                                                                            =:=
                                                                            false
                                                                            orelse
                                                                            _7
                                                                            =:=
                                                                            nil ->
                                                                        _partition@1;
                                                                    _8 ->
                                                                        _8
                                                                end),
                                           case
                                               'Elixir.Access':get(_project@1,
                                                                   test_coverage)
                                           of
                                               _9
                                                   when
                                                       _9 =:= false
                                                       orelse
                                                       _9 =:= nil ->
                                                   [];
                                               _10 ->
                                                   _10
                                           end),
                ('Elixir.Access':get(_cover@1, tool)):start(_compile_path@1,
                                                            _cover@1)
        end,
    case 'Elixir.Mix':shell() of
        #{print_app := _12} ->
            elixir_erl_pass:parens_map_field(print_app, _12);
        _12 ->
            _12:print_app()
    end,
    _app_start_args@1 =
        case
            case 'Elixir.Access':get(_opts@2, slowest) of
                _13
                    when
                        _13 =:= false
                        orelse
                        _13 =:= nil ->
                    'Elixir.Access':get(_opts@2, slowest_modules);
                _14 ->
                    _14
            end
        of
            _15
                when
                    _15 =:= false
                    orelse
                    _15 =:= nil ->
                _args@1;
            _ ->
                [<<"--preload-modules">> | _args@1]
        end,
    'Elixir.Mix.Task':run(<<"app.start">>, _app_start_args@1),
    _shell@1 = 'Elixir.Mix':shell(),
    _test_elixirc_options@1 =
        case 'Elixir.Access':get(_project@1, test_elixirc_options) of
            _16
                when
                    _16 =:= false
                    orelse
                    _16 =:= nil ->
                [];
            _17 ->
                _17
        end,
    {_test_elixirc_options@2, _opts@3} =
        case not 'Elixir.Keyword':get(_opts@2, breakpoints, false) of
            true ->
                {_test_elixirc_options@1, _opts@2};
            false ->
                case 'Elixir.IEx':'started?'() of
                    _18
                        when
                            _18 /= nil
                            andalso
                            _18 /= false ->
                        {'Elixir.Keyword':put(_test_elixirc_options@1,
                                              debug_info, true),
                         _opts@2};
                    _ ->
                        case true of
                            true ->
                                ('Elixir.Mix':shell()):error(<<"you mus"
                                                               "t run "
                                                               "\"iex -"
                                                               "S mix t"
                                                               "est\" w"
                                                               "hen usi"
                                                               "ng -b/-"
                                                               "-breakp"
                                                               "oints">>),
                                {_test_elixirc_options@1,
                                 'Elixir.Keyword':delete(_opts@2,
                                                         breakpoints)};
                            false ->
                                error(cond_clause)
                        end
                end
        end,
    {_ex_unit_opts@1, _allowed_files@1} = process_ex_unit_opts(_opts@3),
    'Elixir.ExUnit':configure(_ex_unit_opts@1),
    _warnings_as_errors?@1 =
        'Elixir.Keyword':get(_opts@3, warnings_as_errors, false),
    _exit_status@1 =
        'Elixir.Keyword':'fetch!'(_ex_unit_opts@1, exit_status),
    _test_paths@1 =
        case 'Elixir.Access':get(_project@1, test_paths) of
            _19
                when
                    _19 =:= false
                    orelse
                    _19 =:= nil ->
                default_test_paths();
            _20 ->
                _20
        end,
    _test_pattern@1 =
        case 'Elixir.Access':get(_project@1, test_pattern) of
            _21
                when
                    _21 =:= false
                    orelse
                    _21 =:= nil ->
                <<"*.{ex,exs}">>;
            _22 ->
                _22
        end,
    case 'Elixir.Access':get(_project@1, warn_test_pattern) of
        _23
            when
                _23 =:= false
                orelse
                _23 =:= nil ->
            nil;
        _ ->
            ('Elixir.Mix':shell()):info(<<"warning: the `:warn_test_pat"
                                          "tern` configuration is depre"
                                          "cated and will be ignored. U"
                                          "se `:test_load_filters` and "
                                          "`:test_ignore_filters` inste"
                                          "ad.\n">>)
    end,
    {_test_files@1, _test_opts@1} =
        case _files@1 /= [] of
            false ->
                {_test_paths@1, []};
            true ->
                'Elixir.ExUnit.Filters':parse_paths(_files@1)
        end,
    {_potential_test_files@1, _directly_included_test_files@1} =
        extract_files(_test_files@1, _test_pattern@1),
    {_load_files@1, __ignored_files@1, _warn_files@1} =
        classify_test_files(_shell@1, _potential_test_files@1,
                            _project@1),
    _load_files@2 =
        case _files@1 /= [] of
            false ->
                _load_files@1;
            true ->
                'Elixir.Enum':uniq(erlang:'++'(_load_files@1,
                                               _directly_included_test_files@1))
        end,
    _matched_test_files@1 =
        filter_by_partition(filter_to_allowed_files(_load_files@2,
                                                    _allowed_files@1),
                            _shell@1, _partitions@1),
    case _warn_files@1 /= [] of
        _24
            when
                _24 =:= false
                orelse
                _24 =:= nil ->
            _24;
        _ ->
            warn_misnamed_test_files(_warn_files@1)
    end,
    try
        _helper_warned?@1 =
            'Elixir.Enum':'any?'(_test_paths@1,
                                 fun(_25) ->
                                        require_test_helper(_shell@1,
                                                            _25)
                                 end),
        'Elixir.ExUnit':configure('Elixir.Keyword':merge(merge_helper_opts(_ex_unit_opts@1),
                                                         _test_opts@1)),
        {'Elixir.Mix.Compilers.Test':require_and_run(_matched_test_files@1,
                                                     _test_paths@1,
                                                     _test_elixirc_options@2,
                                                     _opts@3),
         _helper_warned?@1}
    of
        {{ok,
          #{excluded := _excluded@1,
            failures := _failures@1,
            'warnings?' := _warnings?@1,
            total := _total@1}},
         _helper_warned?@2} ->
            'Elixir.Mix':shell(_shell@1),
            case _cover@2 of
                _26
                    when
                        _26 =:= false
                        orelse
                        _26 =:= nil ->
                    _26;
                _ ->
                    _cover@2()
            end,
            case
                case
                    case _warnings_as_errors?@1 of
                        false ->
                            false;
                        true ->
                            case
                                case _warnings?@1 of
                                    false ->
                                        _helper_warned?@2;
                                    true ->
                                        true;
                                    _32 ->
                                        error({badbool, 'or', _32})
                                end
                            of
                                false ->
                                    _warn_files@1 /= [];
                                true ->
                                    true;
                                _33 ->
                                    error({badbool, 'or', _33})
                            end;
                        _34 ->
                            error({badbool, 'and', _34})
                    end
                of
                    false ->
                        false;
                    true ->
                        _failures@1 == 0;
                    _35 ->
                        error({badbool, 'and', _35})
                end
            of
                _31
                    when
                        _31 /= nil
                        andalso
                        _31 /= false ->
                    abort_due_to_warnings(_shell@1, _opts@3);
                _ ->
                    case
                        case _failures@1 > 0 of
                            false ->
                                false;
                            true ->
                                'Elixir.Access':get(_opts@3, raise)
                        end
                    of
                        _30
                            when
                                _30 /= nil
                                andalso
                                _30 /= false ->
                            raise_with_shell(_shell@1,
                                             <<"\"mix test\" failed">>);
                        _ ->
                            case
                                case
                                    case _warnings_as_errors?@1 of
                                        false ->
                                            false;
                                        true ->
                                            _warnings?@1;
                                        _36 ->
                                            error({badbool, 'and', _36})
                                    end
                                of
                                    false ->
                                        false;
                                    true ->
                                        _failures@1 > 0;
                                    _37 ->
                                        error({badbool, 'and', _37})
                                end
                            of
                                _29
                                    when
                                        _29 /= nil
                                        andalso
                                        _29 /= false ->
                                    'Elixir.System':at_exit(fun(_) ->
                                                                   exit({shutdown,
                                                                         _exit_status@1
                                                                         +
                                                                         1})
                                                            end);
                                _ ->
                                    case _failures@1 > 0 of
                                        true ->
                                            'Elixir.System':at_exit(fun(_) ->
                                                                           exit({shutdown,
                                                                                 _exit_status@1})
                                                                    end);
                                        false ->
                                            case
                                                case
                                                    _excluded@1
                                                    ==
                                                    _total@1
                                                of
                                                    false ->
                                                        false;
                                                    true ->
                                                        'Elixir.Keyword':'has_key?'(_opts@3,
                                                                                    only)
                                                end
                                            of
                                                _28
                                                    when
                                                        _28 /= nil
                                                        andalso
                                                        _28 /= false ->
                                                    nothing_executed(_shell@1,
                                                                     <<"--onl"
                                                                       "y">>,
                                                                     _opts@3);
                                                _ ->
                                                    case
                                                        case
                                                            _excluded@1
                                                            ==
                                                            _total@1
                                                        of
                                                            false ->
                                                                false;
                                                            true ->
                                                                'Elixir.Keyword':'has_key?'(_opts@3,
                                                                                            name_pattern)
                                                        end
                                                    of
                                                        _27
                                                            when
                                                                _27
                                                                /=
                                                                nil
                                                                andalso
                                                                _27
                                                                /=
                                                                false ->
                                                            nothing_executed(_shell@1,
                                                                             <<"--nam"
                                                                               "e-pat"
                                                                               "tern">>,
                                                                             _opts@3);
                                                        _ ->
                                                            case true of
                                                                true ->
                                                                    ok;
                                                                false ->
                                                                    error(cond_clause)
                                                            end
                                                    end
                                            end
                                    end
                            end
                    end
            end;
        {noop, _} ->
            case
                case _warnings_as_errors?@1 of
                    false ->
                        false;
                    true ->
                        _warn_files@1 /= [];
                    _41 ->
                        error({badbool, 'and', _41})
                end
            of
                _40
                    when
                        _40 /= nil
                        andalso
                        _40 /= false ->
                    abort_due_to_warnings(_shell@1, _opts@3);
                _ ->
                    case 'Elixir.Access':get(_opts@3, stale) of
                        _39
                            when
                                _39 /= nil
                                andalso
                                _39 /= false ->
                            ('Elixir.Mix':shell()):info(<<"No stale tes"
                                                          "ts">>);
                        _ ->
                            case
                                case
                                    'Elixir.Access':get(_opts@3, failed)
                                of
                                    _42
                                        when
                                            _42 =:= false
                                            orelse
                                            _42 =:= nil ->
                                        _files@1 == [];
                                    _43 ->
                                        _43
                                end
                            of
                                _38
                                    when
                                        _38 /= nil
                                        andalso
                                        _38 /= false ->
                                    ('Elixir.Mix':shell()):info(<<"There"
                                                                  " are "
                                                                  "no te"
                                                                  "sts t"
                                                                  "o run">>);
                                _ ->
                                    case true of
                                        true ->
                                            _message@1 =
                                                <<"Paths given to \"mix"
                                                  " test\" did not matc"
                                                  "h any directory/file"
                                                  ": ">>,
                                            raise_or_error_at_exit(_shell@1,
                                                                   <<_message@1/binary,
                                                                     ('Elixir.Enum':join(_files@1,
                                                                                         <<", ">>))/binary>>,
                                                                   _opts@3);
                                        false ->
                                            error(cond_clause)
                                    end
                            end
                    end
            end,
            ok
    catch
        _kind@1:_reason@1:___STACKTRACE__@1 ->
            _file@1 = get_manifest_path(_opts@3),
            'Elixir.ExUnit.Filters':'fail_all!'(_file@1),
            erlang:raise(_kind@1, _reason@1, ___STACKTRACE__@1)
    end.
get_test_ignore_filters(_shell@1, _project@1) ->
    _elixirc_paths@1 =
        case 'Elixir.Access':get(_project@1, elixirc_paths) of
            _1
                when
                    _1 =:= false
                    orelse
                    _1 =:= nil ->
                [];
            _2 ->
                _2
        end,
    case 'Elixir.Keyword':get(_project@1, test_ignore_filters, []) of
        _list@1 when is_list(_list@1) ->
            erlang:'++'([fun(_3) ->
                                'Elixir.String':'ends_with?'(_3,
                                                             <<"_helper"
                                                               ".exs">>)
                         end,
                         fun(_file@1) ->
                                'Elixir.Enum':'any?'(_elixirc_paths@1,
                                                     fun(_4) ->
                                                            'Elixir.String':'starts_with?'(_file@1,
                                                                                           _4)
                                                     end)
                         end],
                        _list@1);
        _other@1 ->
            raise_with_shell(_shell@1,
                             <<"Invalid configuration for :test_ignore_"
                               "filters, expected a list, got: ",
                               ('Elixir.Kernel':inspect(_other@1))/binary>>)
    end.
warn_misnamed_test_files(_ignored@1) ->
    ('Elixir.Mix':shell()):info(<<"warning: the following files do not "
                                  "match any of the configured `:test_l"
                                  "oad_filters` / `:test_ignore_filters"
                                  "`:\n\n",
                                  ('Elixir.Enum':join(_ignored@1,
                                                      <<"\n">>))/binary,
                                  "\n\nThis might indicate a typo in a "
                                  "test file name (for example, using "
                                  "\"foo_tests.exs\" instead of \"foo_t"
                                  "est.exs\").\n\nSee the configuration"
                                  " for `:test_pattern` under `mix help"
                                  " test` for more information.\n">>).
%% Official installed module: Mix.Compilers.Test
%% BEAM: /opt/homebrew/Cellar/elixir/1.20.4/lib/elixir/bin/../lib/mix/ebin/Elixir.Mix.Compilers.Test.beam
%% BEAM SHA-256: be97b643c66284612f57689660e4269f70862447e37364a4f9ea6ecb60ceb0a5
%% Compile information: [version: ~c"10.0.3", options: [:no_spawn_compiler_process, :from_core, :no_core_prepare, :no_auto_import, {:no_warn_undefined, ExUnit}], source: ~c"/private/tmp/elixir-20260828-4709-q6w1ex/elixir-1.20.4/lib/mix/lib/mix/compilers/test.ex"]

require_and_run(_matched_test_files@1, _test_paths@1, _opts@1) ->
    _dry_run@1 = 'Elixir.Keyword':get(_opts@1, dry_run, false),
    _stale@1 = 'Elixir.Keyword':get(_opts@1, stale, false),
    _max_requires@1 = 'Elixir.Access':get(_opts@1, max_requires),
    {_test_files@1, _stale_manifest_pid@1,
     _parallel_require_callbacks@1} =
        case
            case _stale@1 of
                false ->
                    false;
                true ->
                    not _dry_run@1;
                _1 ->
                    error({badbool, 'and', _1})
            end
        of
            _2
                when
                    _2 =:= false
                    orelse
                    _2 =:= nil ->
                {_matched_test_files@1, nil, []};
            _ ->
                set_up_stale(_matched_test_files@1, _test_paths@1,
                             _opts@1)
        end,
    _shared_require_options@1 =
        case _max_requires@1 of
            _3
                when
                    _3 =:= false
                    orelse
                    _3 =:= nil ->
                [{return_diagnostics, true}];
            _ ->
                [{max_concurrency, _max_requires@1},
                 {return_diagnostics, true}]
        end,
    'Elixir.Application':ensure_all_started(ex_unit),
    case _test_files@1 == [] of
        true ->
            _formatters@1 =
                'Elixir.Application':'fetch_env!'(ex_unit, formatters),
            try
                'Elixir.Application':put_env(ex_unit, formatters, []),
                _ = 'Elixir.ExUnit':run(),
                noop
            after
                'Elixir.Application':put_env(ex_unit, formatters,
                                             _formatters@1)
            end;
        false ->
            case
                'Elixir.Keyword':get(_opts@1, profile_require)
                ==
                <<"time">>
            of
                true ->
                    'Elixir.Kernel.ParallelCompiler':require(_test_files@1,
                                                             erlang:'++'([{profile,
                                                                           time}],
                                                                         _shared_require_options@1)),
                    noop;
                false ->
                    case true of
                        true ->
                            _task@1 = 'Elixir.ExUnit':async_run(),
                            _seed@1 =
                                'Elixir.Application':'fetch_env!'(ex_unit,
                                                                  seed),
                            _rand_algorithm@1 =
                                'Elixir.Application':'fetch_env!'(ex_unit,
                                                                  rand_algorithm),
                            _test_files@2 =
                                shuffle(_seed@1, _rand_algorithm@1,
                                        _test_files@1),
                            try
                                _parallel_require_options@1 =
                                    erlang:'++'(_shared_require_options@1,
                                                _parallel_require_callbacks@1),
                                _warnings?@1 =
                                    case
                                        'Elixir.Kernel.ParallelCompiler':require(_test_files@2,
                                                                                 _parallel_require_options@1)
                                    of
                                        {ok, _,
                                         #{compile_warnings := _c@1,
                                           runtime_warnings := _r@1}}
                                            when
                                                _c@1 /= []
                                                orelse
                                                _r@1 /= [] ->
                                            true;
                                        {ok, _, _} ->
                                            false;
                                        {error, _, _} ->
                                            exit({shutdown, 1})
                                    end,
                                #{failures := _failures@1} =
                                    _results@1 =
                                        'Elixir.ExUnit':await_run(_task@1),
                                case _failures@1 == 0 of
                                    false ->
                                        nil;
                                    true ->
                                        agent_write_manifest(_stale_manifest_pid@1)
                                end,
                                {ok,
                                 maps:put('warnings?', _warnings?@1,
                                          _results@1)}
                            catch
                                _kind@1:_reason@1:___STACKTRACE__@2 ->
                                    'Elixir.Task':shutdown(_task@1),
                                    erlang:raise(_kind@1, _reason@1,
                                                 ___STACKTRACE__@2)
                            after
                                agent_stop(_stale_manifest_pid@1)
                            end;
                        false ->
                            error(cond_clause)
                    end
            end
    end.
require_and_run(_matched_test_files@1, _test_paths@1, _elixirc_opts@1,
                _opts@1) ->
    _elixirc_opts@2 =
        'Elixir.Keyword':merge([{docs, false},
                                {debug_info, false},
                                {infer_signatures, false}],
                               _elixirc_opts@1),
    _previous_opts@1 = 'Elixir.Code':compiler_options(_elixirc_opts@2),
    try
        require_and_run(_matched_test_files@1, _test_paths@1, _opts@1)
    after
        'Elixir.Code':compiler_options(_previous_opts@1)
    end.
