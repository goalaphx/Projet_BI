import { Component, Inject, NgZone, PLATFORM_ID, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';

// amCharts Imports
import * as am5 from '@amcharts/amcharts5';
import * as am5xy from '@amcharts/amcharts5/xy';
import * as am5map from '@amcharts/amcharts5/map';
import * as am5percent from "@amcharts/amcharts5/percent";
import * as am5wc from "@amcharts/amcharts5/wc"; 
import am5geodata_worldLow from '@amcharts/amcharts5-geodata/worldLow';
import am5themes_Animated from '@amcharts/amcharts5/themes/Animated';

import { ApiService } from '../services/api';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.css']
})
export class DashboardComponent implements OnInit, OnDestroy {
  
  currentTab = 1;
  private roots: am5.Root[] = []; // Store chart instances to dispose later

  constructor(
    @Inject(PLATFORM_ID) private platformId: Object,
    private zone: NgZone,
    private api: ApiService,
    private cdr: ChangeDetectorRef // <--- 1. Inject ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      this.loadTab(1);
    }
  }

  // --- ROBUST TAB SWITCHING ---
  setTab(tabIndex: number) {
    if (this.currentTab === tabIndex) return;

    // 1. Dispose of ALL old charts first to prevent memory leaks
    this.roots.forEach(root => {
      // Check if root exists before disposing
      if (root) root.dispose();
    });
    this.roots = [];

    // 2. Change the active tab variable
    this.currentTab = tabIndex;

    // 3. Force Angular to update the HTML immediately
    this.cdr.detectChanges();

    // 4. Wait 100ms for the <div> to be fully painted, then load the chart
    // This delay is crucial for *ngIf + amCharts to work together
    setTimeout(() => {
      this.loadTab(tabIndex);
    }, 100);
  }

  loadTab(index: number) {
    // Safety Check: Ensure the target DIV actually exists before running
    if (index === 1 && document.getElementById("chartdiv")) {
      this.api.getYearStats().subscribe(data => this.createBarChart(data));
    } 
    else if (index === 2 && document.getElementById("piediv")) {
      this.api.getQuartileStats().subscribe(data => this.createPieChart(data));
    } 
    else if (index === 3 && document.getElementById("mapdiv")) {
      this.api.getCountryStats().subscribe(data => this.createMap(data));
    } 
    else if (index === 4 && document.getElementById("worddiv")) {
      this.api.getKeywordStats().subscribe(data => this.createWordCloud(data));
    }
    else {
      // If the DIV is missing, try again in 100ms
      console.warn("Container not ready yet, retrying...");
      setTimeout(() => this.loadTab(index), 100);
    }
  }
  // --- CHART 1: BAR (Trends) ---
  createBarChart(apiData: any[]): void {
    this.zone.runOutsideAngular(() => {
      let root = am5.Root.new("chartdiv");
      root.setThemes([am5themes_Animated.new(root)]);

      let chart = root.container.children.push(am5xy.XYChart.new(root, {
        panX: true, panY: true, wheelX: "panX", wheelY: "zoomX"
      }));

      // Add Cursor
      let cursor = chart.set("cursor", am5xy.XYCursor.new(root, {}));
      cursor.lineY.set("visible", false);

      let xRenderer = am5xy.AxisRendererX.new(root, { minGridDistance: 30 });
      xRenderer.labels.template.setAll({ rotation: -45, centerY: am5.p50, centerX: am5.p100 });

      let xAxis = chart.xAxes.push(am5xy.CategoryAxis.new(root, {
        categoryField: "year",
        renderer: xRenderer,
        tooltip: am5.Tooltip.new(root, {})
      }));

      let yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, {
        renderer: am5xy.AxisRendererY.new(root, {})
      }));

      let series = chart.series.push(am5xy.ColumnSeries.new(root, {
        name: "Publications",
        xAxis: xAxis, yAxis: yAxis, valueYField: "count", categoryXField: "year",
        tooltip: am5.Tooltip.new(root, { labelText: "{valueY} Papers" })
      }));

      // Styles
      series.columns.template.setAll({ cornerRadiusTL: 5, cornerRadiusTR: 5 });
      series.columns.template.adapters.add("fill", (fill, target) => {
        return chart.get("colors")?.getIndex(series.columns.indexOf(target));
      });

      xAxis.data.setAll(apiData);
      series.data.setAll(apiData);
      
      this.roots.push(root);
    });
  }

  // --- CHART 2: PIE (Quality) ---
  createPieChart(apiData: any[]): void {
    this.zone.runOutsideAngular(() => {
      let root = am5.Root.new("piediv");
      root.setThemes([am5themes_Animated.new(root)]);

      let chart = root.container.children.push(am5percent.PieChart.new(root, {
        layout: root.verticalLayout,
        innerRadius: am5.percent(50) // Donut style looks more modern
      }));

      let series = chart.series.push(am5percent.PieSeries.new(root, {
        valueField: "value", categoryField: "category",
        alignLabels: false
      }));

      series.labels.template.setAll({ textType: "circular", radius: 4 });
      series.data.setAll(apiData);

      // Legend
      let legend = chart.children.push(am5.Legend.new(root, {
        centerX: am5.percent(50), x: am5.percent(50), marginTop: 15, marginBottom: 15
      }));
      legend.data.setAll(series.dataItems);

      this.roots.push(root);
    });
  }

  // --- CHART 3: MAP (Geography) ---
  createMap(apiData: any[]): void {
    this.zone.runOutsideAngular(() => {
      let root = am5.Root.new("mapdiv");
      root.setThemes([am5themes_Animated.new(root)]);

      let chart = root.container.children.push(am5map.MapChart.new(root, {
        panX: "rotateX", panY: "translateY", projection: am5map.geoMercator()
      }));

      let polygonSeries = chart.series.push(am5map.MapPolygonSeries.new(root, {
        geoJSON: am5geodata_worldLow, exclude: ["AQ"],
        valueField: "value", calculateAggregates: true
      }));

      polygonSeries.set("heatRules", [{
        target: polygonSeries.mapPolygons.template,
        dataField: "value",
        min: am5.color(0xffffff),
        max: am5.color(0xff0000),
        key: "fill",
        stops: [
          { color: am5.color(0xffffff) },
          { color: am5.color(0xffff00) },
          { color: am5.color(0xffa500) },
          { color: am5.color(0xff0000) }
        ]
      }]);

      let mapData = apiData.map(item => ({
        id: this.getCountryCode(item.country),
        name: item.country,
        value: item.count
      })).filter(item => item.id);

      polygonSeries.data.setAll(mapData);
      
      polygonSeries.mapPolygons.template.setAll({
        tooltipText: "{name}: {value}", interactive: true
      });
      
      this.roots.push(root);
    });
  }

  // --- CHART 4: WORD CLOUD (Topics) ---
  createWordCloud(apiData: any[]): void {
    this.zone.runOutsideAngular(() => {
      let root = am5.Root.new("worddiv");
      root.setThemes([am5themes_Animated.new(root)]);

      let series = root.container.children.push(am5wc.WordCloud.new(root, {
        categoryField: "text",
        valueField: "value",
        maxFontSize: am5.percent(15), // Reduced size to fit more words
        minFontSize: am5.percent(5)
      }));

      // Better Coloring Strategy
      series.labels.template.setAll({
        fontFamily: "Arial",
        paddingTop: 5, paddingBottom: 5, paddingLeft: 5, paddingRight: 5
      });
      
      // Use standard color set instead of pure random for better readability
      series.labels.template.adapters.add("fill", (fill, target) => {
        return am5.Color.fromAny(this.getRandomColor()); 
      });

      series.data.setAll(apiData);
      this.roots.push(root);
    });
  }

  // Helpers
  getRandomColor(): string {
    const colors = ["#007bff", "#6610f2", "#6f42c1", "#e83e8c", "#dc3545", "#fd7e14", "#ffc107", "#28a745", "#20c997", "#17a2b8"];
    return colors[Math.floor(Math.random() * colors.length)];
  }

  getCountryCode(name: string): string | undefined {
    const mapping: {[key: string]: string} = {
      "USA": "US", "United States": "US", "Canada": "CA", "Brazil": "BR",
      "China": "CN", "P.R. China": "CN", "India": "IN", "Japan": "JP", "South Korea": "KR", "Singapore": "SG",
      "Australia": "AU", "UK": "GB", "United Kingdom": "GB", "France": "FR", "Germany": "DE", "Italy": "IT",
      "Spain": "ES", "Russia": "RU", "Switzerland": "CH", "Netherlands": "NL", "Sweden": "SE",
      "Morocco": "MA", "South Africa": "ZA", "UAE": "AE"
    };
    return mapping[name] || undefined;
  }

  ngOnDestroy(): void {
    this.roots.forEach(root => root.dispose());
  }
}