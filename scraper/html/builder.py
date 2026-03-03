def attach_header_in_html() -> str:
    """Return the full <head> block used by every generated HTML page."""
    return r"""<head>
                    <meta charset="UTF-8">
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet"/>
                    <link crossorigin="anonymous" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" integrity="sha384-rbsA2VBKQhggwzxH7pPCaAqO46MgnOM80zW1RWuH61DGLwZJEdK2Kadq2F9CUG65" rel="stylesheet"/>
                    <script crossorigin="anonymous" integrity="sha384-kenU1KFdBIe4zVF0s0G1M5b4hcpxyD9F7jL+jjXkk+Q2h455rYXK/7HAuoJl+0I4" src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js">
                    </script>
                    <script src="https://md-block.verou.me/md-block.js" type="module">
                    </script>
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/9000.0.1/prism.min.js">
                    </script>
                    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6">
                    </script>
                    <script async="" src="https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-MML-AM_CHTML" type="text/javascript">
                    MathJax.Hub.Config({
                                        TeX: {
                                            Macros: {
                                            "exclude": "\\def\\exclude#1{}"
                                            }
                                        },
                                        tex2jax: {
                                            inlineMath: [["$", "$"], ["\\(", "\\)"], ["$$", "$$"], ["\\[", "\\]"]],
                                            processEscapes: true,
                                            processEnvironments: true,
                                            skipTags: ['script', 'noscript', 'style', 'textarea', 'pre']
                                        },
                                        CommonHTML: {
                                                            scale: 80
                                                        },
                                        });

                                        MathJax.Hub.Register.StartupHook("TeX Jax Ready", function() {
                                        MathJax.Hub.Insert(MathJax.InputJax.TeX.Definitions.macros, {
                                            exclude: "exclude"
                                        });
                                        });
                    </script>
                    <script>
                    function lcGetCookie(name) {
                        const value = '; ' + document.cookie;
                        const parts = value.split('; ' + name + '=');
                        if (parts.length === 2) return parts.pop().split(';').shift();
                        return null;
                    }
                    function lcSetCookie(name, value, days) {
                        const expires = new Date(Date.now() + days * 864e5).toUTCString();
                        document.cookie = name + '=' + value + '; expires=' + expires + '; path=/';
                    }
                    function applyDarkMode() {
                        $('body').addClass('dark');
                        $('div[style*="background: wheat;"]').addClass('dark-banner');
                        $('div[style*="background: beige;"]').addClass('dark-banner-sq');
                        $('div[id*="v-pills-tabContent"]').addClass('tab-content dark');
                        $('table').removeClass('table-color').addClass('table-color-dark');
                    }
                    function applyLightMode() {
                        $('body').removeClass('dark');
                        $('div[style*="background: wheat;"]').removeClass('dark-banner');
                        $('div[style*="background: beige;"]').removeClass('dark-banner-sq');
                        $('div[id*="v-pills-tabContent"]').removeClass('dark').addClass('tab-content');
                        $('table').removeClass('table-color-dark').addClass('table-color');
                    }
                    document.addEventListener('DOMContentLoaded', function() {
                                                const carousel = document.querySelectorAll('.carousel');
                                                const items = Array.from(document.querySelectorAll('.carousel-item'));
                                                const maxWidth = Math.max(...items.map(item => item.querySelector('img').clientWidth));
                                                for (let i = 0; i < carousel.length; i++) {
                                                    carousel[i].style.width = maxWidth + 'px';
                                                }
                                                if (lcGetCookie('lc_dark_mode') === 'true') {
                                                    applyDarkMode();
                                                }
                                                $( ".change" ).on("click", function() {
                                                    if( $( "body" ).hasClass( "dark" )) {
                                                        applyLightMode();
                                                        lcSetCookie('lc_dark_mode', 'false', 365);
                                                    } else {
                                                        applyDarkMode();
                                                        lcSetCookie('lc_dark_mode', 'true', 365);
                                                    }
                                                });
                                    });
                    </script>
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.4.0/jquery.min.js"></script>
                    <style>
                                body {
                                    overflow-x: hidden;
                                    background-color: lightblue;
                                    left: 10% !important;
                                    right: 10% !important;
                                    position: absolute;
                                    }
                                    .similar-questions-container {
                                        display: flex;
                                        justify-content: space-between;
                                        }
                                        .left::after {
                                        content: "-";
                                        margin-left: 5px;
                                        }
                                        .right::before {
                                        content: "-";
                                        margin-right: 5px;
                                        }
                                    .mode {
                                        float:right;
                                    }
                                    .dark.tab-content{
                                            background-color: #00000036 !important;
                                    }
                                    .dark-banner-sq{
                                            background-color: #3b3451b8 !important;
                                    }
                                    .tab-content{
                                        background: cornsilk !important;
                                    }
                                    .change {
                                        cursor: pointer;
                                        text-align: center;
                                        padding: 5px;
                                        margin-left: 8px;
                                    }
                                    .dark{
                                        background-color: #222;
                                        color: #e6e6e6;
                                    }
                                    .dark-banner{
                                        background-color: darkslategray !important;
                                        color: #e6e6e6 !important;
                                    }
                                    .carousel-control-prev > span,
                                    .carousel-control-next > span {
                                    background-color: #007bff;
                                    border-color: #007bff;
                                    }
                                    img {
                                        width: auto;
                                        height: auto;
                                        max-width: 100%;
                                        max-height: 100%;
                                    }
                                    .dark img {
                                        filter: invert(0.867) hue-rotate(180deg);
                                    }
                                    /* ── Tables ── */
                                    .table-color { background-color: #fff; color: #222; }
                                    .table-color-dark { background-color: #2c2c2c; color: #e6e6e6; }
                                    .table-color td, .table-color th { border-color: #dee2e6 !important; }
                                    .table-color-dark td, .table-color-dark th { border-color: #444 !important; color: #e6e6e6; }
                                    /* ── Difficulty badges ── */
                                    .badge-easy   { background-color: #00b8a3; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }
                                    .badge-medium { background-color: #ffc01e; color: #333; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }
                                    .badge-hard   { background-color: #ef4743; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }
                                    .dark .badge-easy   { background-color: #007d72; }
                                    .dark .badge-medium { background-color: #b38600; color: #eee; }
                                    .dark .badge-hard   { background-color: #b02e2c; }
                                    /* ── Frequency bar ── */
                                    .freq-bar-wrap { background:#ddd; border-radius:4px; width:80px; height:8px; display:inline-block; vertical-align:middle; }
                                    .freq-bar      { background:#4e9af1; border-radius:4px; height:8px; }
                                    .dark .freq-bar-wrap { background:#555; }
                                    /* ── Company cards grid ── */
                                    .company-grid { display:flex; flex-wrap:wrap; gap:8px; padding:12px 0; }
                                    .company-card { display:inline-block; padding:6px 14px; border-radius:6px;
                                                    background:#e8f0fe; color:#174ea6; text-decoration:none;
                                                    font-size:0.9em; font-weight:500;
                                                    border:1px solid #c5d3f0; transition: all .15s; }
                                    .company-card:hover { background:#174ea6; color:#fff; text-decoration:none; }
                                    .dark .company-card { background:#2a3a5c; color:#a8c4ff; border-color:#3a5080; }
                                    .dark .company-card:hover { background:#3d5a8a; color:#fff; }
                                    /* ── Search box ── */
                                    .lc-search { margin:12px 0; padding:6px 12px; border-radius:6px;
                                                 border:1px solid #ccc; width:100%; max-width:400px;
                                                 font-size:1em; }
                                    .dark .lc-search { background:#333; color:#e6e6e6; border-color:#555; }
                                    /* ── Difficulty filter buttons ── */
                                    .diff-btn { padding:4px 12px; border-radius:4px; border:1px solid #ccc;
                                                background:#f5f5f5; color:#333; cursor:pointer; font-size:0.85em; transition:all .15s; }
                                    .diff-btn.active { color:#fff; border-color:transparent; }
                                    .diff-btn[data-diff="all"].active  { background:#555; }
                                    .diff-btn[data-diff="Easy"].active   { background:#00b8a3; }
                                    .diff-btn[data-diff="Medium"].active { background:#ffc01e; color:#333; }
                                    .diff-btn[data-diff="Hard"].active   { background:#ef4743; }
                                    .dark .diff-btn { background:#333; color:#ccc; border-color:#555; }
                                    .dark .diff-btn[data-diff="Easy"].active   { background:#007d72; }
                                    .dark .diff-btn[data-diff="Medium"].active { background:#b38600; color:#eee; }
                                    .dark .diff-btn[data-diff="Hard"].active   { background:#b02e2c; }
                                    /* ── Inline company tags ── */
                                    .company-tag { display:inline-block; padding:1px 7px; margin:2px 1px;
                                                   border-radius:3px; font-size:0.77em;
                                                   background:#e8f0fe; color:#174ea6; border:1px solid #c5d3f0; }
                                    .dark .company-tag { background:#2a3a5c; color:#a8c4ff; border-color:#3a5080; }
                                    /* ── Company stat pill ── */
                                    .co-pill { display:inline-flex; align-items:center; gap:4px;
                                               padding:3px 10px 3px 8px; margin:3px 3px;
                                               border-radius:20px; font-size:0.82em; font-weight:500;
                                               background:#eef2ff; color:#3730a3; border:1px solid #c7d2fe;
                                               text-decoration:none; }
                                    .co-pill .co-cnt { background:#3730a3; color:#fff;
                                                        border-radius:10px; padding:0 6px;
                                                        font-size:0.78em; font-weight:700; }
                                    .dark .co-pill { background:#1e2a4a; color:#93c5fd; border-color:#2d4a7a; }
                                    .dark .co-pill .co-cnt { background:#2563eb; }
                                    /* ── Stat period heading ── */
                                    .stat-period { display:inline-block; font-size:0.78em; font-weight:600;
                                                   padding:2px 10px; border-radius:4px; margin-bottom:6px;
                                                   background:#fef3c7; color:#92400e; border:1px solid #fcd34d; }
                                    .dark .stat-period { background:#3a2a0a; color:#fcd34d; border-color:#92400e; }
                                    .stat-section { margin-bottom:10px; padding:8px 10px;
                                                    border-radius:6px; background:#fffbeb;
                                                    border:1px solid #fde68a; }
                                    .dark .stat-section { background:#1c1a0f; border-color:#4a3a0a; }
                                    /* ── Similar questions table ── */
                                    .sim-q-table { width:100%; border-collapse:collapse; font-size:0.9em; }
                                    .sim-q-table td { padding:5px 8px; border-bottom:1px solid #e5e7eb; vertical-align:middle; }
                                    .dark .sim-q-table td { border-color:#374151; }
                                    .sim-q-table tr:last-child td { border-bottom:none; }
                                    .sim-q-table tr:hover td { background:rgba(0,0,0,0.03); }
                                    .dark .sim-q-table tr:hover td { background:rgba(255,255,255,0.04); }
                                    /* ── Question sections ── */
                                    .q-section { font-size: 1rem !important; 
                                                 margin:18px 0; padding:14px 18px;
                                                 border-radius:8px; background:#fff;
                                                 border:1px solid #e5e7eb;
                                                 overflow:hidden; box-sizing:border-box; }
                                    .dark .q-section { background:#1e1e1e; border-color:#333; }
                                    .q-section h5, .q-section h3 { margin-top:0; margin-bottom:10px;
                                                                    font-size:1em; font-weight:700;
                                                                    text-transform:uppercase; letter-spacing:.04em;
                                                                    color:#6b7280; }
                                    .dark .q-section h5, .dark .q-section h3 { color:#9ca3af; }
                                    /* ── md-block containment ── */
                                    md-block { display:block; width:100%; box-sizing:border-box;
                                               overflow-wrap:break-word; word-break:break-word; }
                                    md-block p, md-block li, md-block pre { max-width:100%; }
                                    /* ── Code block ── */
                                    .code-wrap { position:relative; }
                                    .code-wrap pre { background:#1e1e2e; color:#cdd6f4;
                                                     padding:16px; border-radius:6px;
                                                     overflow-x:auto; font-size:0.88em;
                                                     line-height:1.6; margin:0; }
                                    .dark .code-wrap pre { background:#111122; }
                                    /* ── Hint items ── */
                                    .hint-item { padding:8px 12px; margin:6px 0;
                                                 border-left:3px solid #6366f1;
                                                 background:#f5f3ff; border-radius:0 6px 6px 0;
                                                }
                                    .dark .hint-item { background:#1a1830; border-color:#4f46e5; }
                                    /* ── Question title header ── */
                                    .q-header { display:flex; align-items:center; flex-wrap:wrap;
                                                gap:10px; margin-bottom:12px; }
                                    .q-title { font-size:1.4em; font-weight:700; margin:0; }
                                    .q-title a { text-decoration:none; color:inherit; }
                                    .q-title a:hover { text-decoration:underline; }
                                    /* ── Bootstrap table hover fix in dark mode ── */
                                    .dark .table-color-dark tbody tr:hover > * {
                                        --bs-table-accent-bg: #3a3a3a;
                                        --bs-table-hover-bg: #3a3a3a;
                                        --bs-table-hover-color: #e6e6e6;
                                        color: #e6e6e6 !important;
                                        background-color: #3a3a3a !important;
                                    }
                                    /* ── Page nav bar ── */
                                    .lc-nav { display:flex; align-items:center; justify-content:space-between;
                                              padding:6px 0; margin-bottom:14px;
                                              border-bottom:1px solid #e5e7eb; }
                                    .dark .lc-nav { border-color:#333; }
                                    .back-btn { display:inline-flex; align-items:center; gap:5px;
                                                padding:5px 12px; border-radius:6px; font-size:0.88em;
                                                background:#f3f4f6; color:#374151; text-decoration:none;
                                                border:1px solid #d1d5db; transition:all .15s; cursor:pointer; }
                                    .back-btn:hover { background:#e5e7eb; color:#111; text-decoration:none; }
                                    .dark .back-btn { background:#2d2d2d; color:#d1d5db; border-color:#444; }
                                    .dark .back-btn:hover { background:#3a3a3a; color:#fff; }
                                    /* ── Sun/moon slider toggle ── */
                                    .dm-switch { display:inline-flex; align-items:center; gap:6px;
                                                 cursor:pointer; user-select:none; font-size:0.9em;
                                                 color:#374151; }
                                    .dark .dm-switch { color:#d1d5db; }
                                    .dm-track { position:relative; width:44px; height:24px;
                                                background:#d1d5db; border-radius:12px;
                                                transition:background .25s; flex-shrink:0; }
                                    .dark .dm-track { background:#4f46e5; }
                                    .dm-thumb { position:absolute; top:3px; left:3px;
                                                width:18px; height:18px; background:#fff;
                                                border-radius:50%; box-shadow:0 1px 3px rgba(0,0,0,.25);
                                                transition:transform .25s; display:flex;
                                                align-items:center; justify-content:center;
                                                font-size:11px; line-height:1; }
                                    .dark .dm-thumb { transform:translateX(20px); }
                                    .dm-sun, .dm-moon { font-size:1em; line-height:1; }
                    </style>
                    <style>
                    mjx-container, .mjx-chtml {
                                        display: inline !important;
                                    }
                    </style>
 """


def attach_page_nav() -> str:
    """Return the top navigation bar (back button + dark mode toggle) used on every page."""
    return (
        '<div class="lc-nav">'
        '<a class="back-btn" href="../index.html">'
        '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
        '<polyline points="15 18 9 12 15 6"/></svg> Back</a>'
        '<label class="dm-switch change" title="Toggle dark mode">'
        '<span class="dm-sun">&#9728;</span>'
        '<span class="dm-track"><span class="dm-thumb"></span></span>'
        '<span class="dm-moon">&#9790;</span>'
        '</label>'
        '</div>'
    )
