import { Component, NgZone, OnInit, OnDestroy, ChangeDetectorRef, Inject, PLATFORM_ID, ViewEncapsulation } from "@angular/core"
import { CommonModule, isPlatformBrowser } from "@angular/common"
import { FormsModule } from "@angular/forms"
import { finalize } from "rxjs/operators";
import { forkJoin } from "rxjs";

// amCharts Imports
import * as am5 from "@amcharts/amcharts5"
import * as am5xy from "@amcharts/amcharts5/xy"
import * as am5map from "@amcharts/amcharts5/map"
import * as am5percent from "@amcharts/amcharts5/percent"
import * as am5wc from "@amcharts/amcharts5/wc"
import * as am5hierarchy from "@amcharts/amcharts5/hierarchy"
import am5geodata_worldLow from "@amcharts/amcharts5-geodata/worldLow"
import am5themes_Animated from "@amcharts/amcharts5/themes/Animated"
import am5themes_Responsive from "@amcharts/amcharts5/themes/Responsive"

// Import Service and Types
import { ApiService, KPIData, DataPoint } from "../services/api"

@Component({
  selector: "app-dashboard",
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: "./dashboard.html",
  styleUrls: ["./dashboard.css"],
  encapsulation: ViewEncapsulation.None
})
export class Dashboard implements OnInit, OnDestroy {
  currentTab = 1
  kpiData: KPIData = { total_pubs: 0, total_citations: 0, avg_impact: 0, total_authors: 0 }
  private roots: am5.Root[] = []
  isLoading = true
  isDarkMode = false

  selectedYear = "All"
  selectedCountry = "All"
  availableYears: string[] = []
  availableCountries: string[] = []

  // Injected properties
  private platformId: Object
  private zone: NgZone
  private api: ApiService
  private cdr: ChangeDetectorRef

  constructor(
    @Inject(PLATFORM_ID) platformId: Object,
    zone: NgZone,
    api: ApiService,
    cdr: ChangeDetectorRef
  ) {
    this.platformId = platformId
    this.zone = zone
    this.api = api
    this.cdr = cdr
  }

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      const saved = localStorage.getItem("dashboard-dark-mode")
      this.isDarkMode = saved ? JSON.parse(saved) : false
      this.applyTheme()
      this.loadFilters()
    }
  }

  toggleDarkMode(): void {
    this.isDarkMode = !this.isDarkMode
    localStorage.setItem("dashboard-dark-mode", JSON.stringify(this.isDarkMode))
    this.applyTheme()
    
    // Refresh charts to apply new theme colors
    this.roots.forEach((r) => r.dispose())
    this.roots = []
    this.loadTab(this.currentTab)
  }

  applyTheme(): void {
    const body = document.body;
    if (this.isDarkMode) {
      body.classList.add("dark-mode")
    } else {
      body.classList.remove("dark-mode")
    }
  }

  // --- DATA LOADING ---
  loadFilters() {
    this.isLoading = true
    this.api.getFilterOptions().subscribe({
      next: (data) => {
        this.availableYears = ["All", ...data.years]
        this.availableCountries = ["All", ...data.countries]
        this.loadKPIs()
        this.loadTab(1)
      },
      error: (err) => {
        console.error("Failed to load filters", err);
        // Safety: ensure loading stops if error occurs
        this.isLoading = false; 
        this.cdr.detectChanges();
      }
    })
  }

  onFilterChange() {
    this.isLoading = true
    this.roots.forEach((r) => r.dispose())
    this.roots = []
    this.loadKPIs()
    this.loadTab(this.currentTab)
  }

  loadKPIs() {
    this.api.getSummaryKPI(this.selectedYear, this.selectedCountry).subscribe((data) => {
      if (data) this.kpiData = data
      // KPI data is light, but good to detect changes just in case
      this.cdr.detectChanges();
    })
  }

  setTab(tabIndex: number) {
    if (this.currentTab === tabIndex) return
    this.isLoading = true
    this.roots.forEach((root) => root?.dispose())
    this.roots = []
    this.currentTab = tabIndex
    
    // This detectChanges renders the HTML Container (div) so standard JS can find it by ID
    this.cdr.detectChanges()
    
    setTimeout(() => {
      this.loadTab(tabIndex)
    }, 50)
  }

  loadTab(index: number) {
    const y = this.selectedYear;
    const c = this.selectedCountry;
    
    let containerId = "";
    if (index === 1) containerId = "chartdiv";
    else if (index === 2) containerId = "piediv";
    else if (index === 3) containerId = "mapdiv";
    else if (index === 4) containerId = "worddiv";
    else if (index === 5) containerId = "networkdiv";

    setTimeout(() => {
      if (!document.getElementById(containerId)) return;

      // === FIX IMPLEMENTED BELOW ===
      // We explicitly call this.cdr.detectChanges() inside finalize
      // to force the view to update and hide the spinner.

      if (index === 1) {
        this.api.getTimeStats(y, c)
          .pipe(finalize(() => {
             this.isLoading = false;
             this.cdr.detectChanges(); // <--- FIX
          }))
          .subscribe((data) => {
            this.createBarChart(data);
          });

      } else if (index === 2) {
        this.api.getQuartileStats(y, c)
          .pipe(finalize(() => {
            this.isLoading = false;
            this.cdr.detectChanges(); // <--- FIX
          }))
          .subscribe((data) => {
            this.createPieChart(data);
          });

      } else if (index === 3) {
        forkJoin([
          this.api.getGeoStats(y, c),
          this.api.getTopAuthors(y, c)
        ])
        .pipe(finalize(() => {
          this.isLoading = false;
          this.cdr.detectChanges(); // <--- FIX
        }))
        .subscribe({
          next: ([geoData, authorData]) => {
            this.createMap(geoData);
            this.createHBarChart(authorData);
          },
          error: (err) => console.error("Error loading Tab 3 data", err)
        });

      } else if (index === 4) {
        this.api.getKeywordStats(y, c)
          .pipe(finalize(() => {
            this.isLoading = false;
            this.cdr.detectChanges(); // <--- FIX
          }))
          .subscribe((data) => {
            this.createWordCloud(data);
          });

      } else if (index === 5) {
        this.api.getCoAuthorNetwork(y, c)
          .pipe(finalize(() => {
            this.isLoading = false;
            this.cdr.detectChanges(); // <--- FIX
          }))
          .subscribe((data) => {
            this.createNetworkGraph(data);
          });
      }
    }, 100);
  }

  // --- CHART LOGIC (THEME ENGINE) ---

  getTheme(root: am5.Root) {
    const myTheme = am5.Theme.new(root);

    const colorText = this.isDarkMode ? am5.color(0xe2e8f0) : am5.color(0x1e293b);
    const colorBackground = this.isDarkMode ? am5.color(0x1e293b) : am5.color(0xffffff);
    const colorGrid = this.isDarkMode ? am5.color(0xffffff) : am5.color(0x000000);

    root.interfaceColors.set("text", colorText);
    root.interfaceColors.set("background", colorBackground);
    root.interfaceColors.set("grid", colorGrid);
    root.interfaceColors.set("alternativeBackground", this.isDarkMode ? am5.color(0x0f172a) : am5.color(0xf1f5f9));

    myTheme.rule("Label").setAll({ fill: colorText });
    myTheme.rule("Grid").setAll({ stroke: colorGrid, strokeOpacity: 0.08 });

    return myTheme;
  }

  createBarChart(apiData: any[]): void {
    this.zone.runOutsideAngular(() => {
      const root = am5.Root.new("chartdiv")
      root.setThemes([am5themes_Animated.new(root), am5themes_Responsive.new(root), this.getTheme(root)])
      
      const chart = root.container.children.push(am5xy.XYChart.new(root, { panX: true, panY: true, wheelX: "panX", wheelY: "zoomX", layout: root.verticalLayout }))
      
      const cursor = chart.set("cursor", am5xy.XYCursor.new(root, { behavior: "none" }));
      cursor.lineY.set("visible", false);

      const xRenderer = am5xy.AxisRendererX.new(root, { minGridDistance: 30, minorGridEnabled: true });
      const xAxis = chart.xAxes.push(am5xy.CategoryAxis.new(root, { categoryField: "_id", renderer: xRenderer, tooltip: am5.Tooltip.new(root, {}) }));
      const yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, { renderer: am5xy.AxisRendererY.new(root, {}) }));

      const series = chart.series.push(am5xy.ColumnSeries.new(root, { xAxis: xAxis, yAxis: yAxis, valueYField: "count", categoryXField: "_id", tooltip: am5.Tooltip.new(root, { labelText: "{valueY}" }) }));
      
      series.columns.template.setAll({ cornerRadiusTL: 5, cornerRadiusTR: 5, strokeOpacity: 0 });
      series.columns.template.adapters.add("fill", (fill, target) => chart.get("colors")!.getIndex(series.columns.indexOf(target)));

      xAxis.data.setAll(apiData);
      series.data.setAll(apiData);
      series.appear(1000);
      chart.appear(1000, 100);
      this.roots.push(root);
    })
  }

  createPieChart(apiData: any[]): void {
    this.zone.runOutsideAngular(() => {
      const root = am5.Root.new("piediv")
      root.setThemes([am5themes_Animated.new(root), this.getTheme(root)])
      
      const chart = root.container.children.push(am5percent.PieChart.new(root, { layout: root.verticalLayout, innerRadius: am5.percent(60) }));
      const series = chart.series.push(am5percent.PieSeries.new(root, { valueField: "count", categoryField: "_id", alignLabels: false }));
      
      series.labels.template.setAll({ textType: "circular", radius: 10 });
      series.slices.template.setAll({ stroke: this.isDarkMode ? am5.color(0x1e293b) : am5.color(0xffffff), strokeWidth: 2 });
      
      series.data.setAll(apiData);
      const legend = chart.children.push(am5.Legend.new(root, { centerX: am5.percent(50), x: am5.percent(50), marginTop: 20 }));
      legend.data.setAll(series.dataItems);
      
      series.appear(1000, 100);
      this.roots.push(root);
    })
  }

  createMap(apiData: any[]): void {
    this.zone.runOutsideAngular(() => {
      const root = am5.Root.new("mapdiv")
      root.setThemes([am5themes_Animated.new(root), this.getTheme(root)])
      
      const chart = root.container.children.push(am5map.MapChart.new(root, { panX: "rotateX", panY: "translateY", projection: am5map.geoMercator() }));
      const polygonSeries = chart.series.push(am5map.MapPolygonSeries.new(root, { geoJSON: am5geodata_worldLow, exclude: ["AQ"], valueField: "value", calculateAggregates: true }));

      polygonSeries.mapPolygons.template.setAll({ tooltipText: "{name}: {value}", interactive: true, strokeWidth: 1, 
        stroke: this.isDarkMode ? am5.color(0x1e293b) : am5.color(0xffffff), 
        fill: this.isDarkMode ? am5.color(0x334155) : am5.color(0xd1d5db) 
      });
      
      polygonSeries.mapPolygons.template.states.create("hover", { fill: am5.color(0xfbbf24) });
      polygonSeries.set("heatRules", [{ target: polygonSeries.mapPolygons.template, dataField: "value", min: am5.color(0xfef08a), max: am5.color(0xdc2626), key: "fill" }]);

      const mapData = apiData.map((item) => ({ id: this.getCountryCode(item.id), name: item.id, value: item.value })).filter((item) => item.id);
      polygonSeries.data.setAll(mapData);
      chart.appear(1000, 100);
      this.roots.push(root);
    })
  }

  createHBarChart(apiData: any[]): void {
    this.zone.runOutsideAngular(() => {
      const root = am5.Root.new("authorsdiv")
      root.setThemes([am5themes_Animated.new(root), this.getTheme(root)])
      
      const chart = root.container.children.push(am5xy.XYChart.new(root, { panX: false, panY: false, wheelX: "panX", wheelY: "zoomX", layout: root.verticalLayout }));
      const yRenderer = am5xy.AxisRendererY.new(root, { minGridDistance: 30, inversed: true });
      yRenderer.labels.template.setAll({ maxWidth: 150, oversizedBehavior: "wrap", textAlign: "end" });

      const yAxis = chart.yAxes.push(am5xy.CategoryAxis.new(root, { categoryField: "_id", renderer: yRenderer }));
      const xAxis = chart.xAxes.push(am5xy.ValueAxis.new(root, { renderer: am5xy.AxisRendererX.new(root, {}) }));
      const series = chart.series.push(am5xy.ColumnSeries.new(root, { xAxis: xAxis, yAxis: yAxis, valueXField: "count", categoryYField: "_id", tooltip: am5.Tooltip.new(root, { labelText: "{valueX}" }) }));
      
      series.columns.template.setAll({ cornerRadiusBR: 5, cornerRadiusTR: 5 });
      series.columns.template.adapters.add("fill", (fill, target) => chart.get("colors")!.getIndex(series.columns.indexOf(target)));
      
      yAxis.data.setAll(apiData);
      series.data.setAll(apiData);
      series.appear(1000);
      this.roots.push(root);
    })
  }

  createWordCloud(apiData: any[]): void {
    this.zone.runOutsideAngular(() => {
      const root = am5.Root.new("worddiv")
      root.setThemes([am5themes_Animated.new(root), this.getTheme(root)])
      
      const series = root.container.children.push(am5wc.WordCloud.new(root, { categoryField: "text", valueField: "weight", maxFontSize: am5.percent(20) }));
      series.labels.template.setAll({ fontFamily: "sans-serif", fontWeight: "600" });
      series.labels.template.adapters.add("fill", () => am5.Color.fromAny(this.getRandomColor()));
      
      series.data.setAll(apiData);
      this.roots.push(root);
    })
  }

  createNetworkGraph(apiData: any): void {
    this.zone.runOutsideAngular(() => {
      const root = am5.Root.new("networkdiv")
      root.setThemes([am5themes_Animated.new(root), this.getTheme(root)])
      
      const series = root.container.children.push(am5hierarchy.ForceDirected.new(root, { singleBranchOnly: false, downDepth: 1, initialDepth: 2, valueField: "value", categoryField: "id", childDataField: "children", idField: "id", linkWithField: "linkWith", manyBodyStrength: -20, centerStrength: 0.8 }));
      
      const data = { id: "Root", children: apiData.nodes.map((n: any) => ({ id: n.id, name: n.id, value: n.value, linkWith: apiData.links.filter((l: any) => l.source === n.id).map((l: any) => l.target) })) };
      series.data.setAll([data]);
      series.circles.template.setAll({ fillOpacity: 0.9, strokeWidth: 2, stroke: this.isDarkMode ? am5.color(0x1e293b) : am5.color(0xffffff) });
      
      this.roots.push(root);
    })
  }

  getRandomColor(): string {
    const colors = ["#4f46e5", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"];
    return colors[Math.floor(Math.random() * colors.length)];
  }

  getCountryCode(name: string): string | undefined {
    const mapping: { [key: string]: string } = { USA: "US", "United States": "US", Canada: "CA", Brazil: "BR", China: "CN", India: "IN", France: "FR", Germany: "DE", UK: "GB", Italy: "IT", Morocco: "MA", Spain: "ES", Japan: "JP", Australia: "AU", Russia: "RU" };
    return mapping[name] || undefined;
  }

  ngOnDestroy(): void {
    this.roots.forEach((root) => root?.dispose())
  }
}