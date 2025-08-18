// Alpine.js components for Duty Tracker

// Dashboard component
function dashboardData() {
  return {
    assignments: [],
    personnel: [],
    posts: [],
    fairnessStats: [],
    postDistributionStats: {},
    stats: {},
    loading: false,
    selectedDate: new Date().toISOString().split("T")[0],
    showAssignmentModal: false,
    showImportModal: false,
    showPostDistribution: false,
    showPersonnelModal: false,
    importing: false,
    recalculating: false,
    personnelDetails: null,
    newAssignment: {
      person_id: "",
      post_id: "",
      duty_date: "",
      start_time: "",
      end_time: "",
      notes: "",
    },
    importData: {
      duty_date: "",
      chat_text: "",
    },

    async init() {
      // Use server data if available, otherwise load from API
      if (window.serverData) {
        this.stats = window.serverData.stats || {};
        this.fairnessStats = window.serverData.fairness_stats || [];
        this.postDistributionStats =
          window.serverData.post_distribution_stats || {};
      }
      await this.loadData();
    },

    async loadData() {
      this.loading = true;
      try {
        const [
          assignmentsRes,
          personnelRes,
          postsRes,
          fairnessRes,
          statsRes,
          postDistributionRes,
        ] = await Promise.all([
          fetch("/api/assignments"),
          fetch("/api/personnel"),
          fetch("/api/posts"),
          fetch("/api/fairness"),
          fetch("/api/dashboard"),
          fetch("/api/post-distribution"),
        ]);

        this.assignments = await assignmentsRes.json();
        this.personnel = await personnelRes.json();
        this.posts = await postsRes.json();

        // Handle fairness stats with error checking
        const fairnessData = await fairnessRes.json();
        this.fairnessStats = Array.isArray(fairnessData) ? fairnessData : [];

        this.stats = await statsRes.json();

        // Handle post distribution stats with error checking
        const postDistData = await postDistributionRes.json();
        this.postDistributionStats = postDistData || {};

        // Add full_name property to personnel for easier display
        this.personnel.forEach((person) => {
          person.full_name = `${person.rank} ${person.name}`;
        });
      } catch (error) {
        console.error("Failed to load data:", error);
        // Ensure arrays are initialized even on error
        this.fairnessStats = this.fairnessStats || [];
        this.personnel = this.personnel || [];
        this.posts = this.posts || [];
        this.assignments = this.assignments || [];
        this.stats = this.stats || {};
        this.postDistributionStats = this.postDistributionStats || {};
      } finally {
        this.loading = false;
      }
    },

    // Get assignments filtered by selected date
    get filteredAssignments() {
      if (!this.selectedDate) return this.assignments;

      return this.assignments.filter((assignment) => {
        const assignmentDate = new Date(assignment.duty_date)
          .toISOString()
          .split("T")[0];
        return assignmentDate === this.selectedDate;
      });
    },

    // Get assignments for display (filtered and sorted)
    get displayAssignments() {
      return this.filteredAssignments
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        .slice(0, 20); // Show more assignments
    },

    openAssignmentModal() {
      this.newAssignment = {
        person_id: "",
        post_id: "",
        duty_date: this.selectedDate,
        start_time: "",
        end_time: "",
        notes: "",
      };
      this.showAssignmentModal = true;
    },

    async createAssignment() {
      try {
        const response = await fetch("/api/assignments", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            ...this.newAssignment,
            duty_date: new Date(this.newAssignment.duty_date).toISOString(),
          }),
        });

        if (response.ok) {
          await this.loadData();
          this.showAssignmentModal = false;
        } else {
          const error = await response.json();
          alert("Failed to create assignment: " + error.detail);
        }
      } catch (error) {
        alert("Failed to create assignment: " + error.message);
      }
    },

    openImportModal() {
      this.importData = {
        duty_date: this.selectedDate || new Date().toISOString().split("T")[0],
        chat_text: "",
      };
      this.showImportModal = true;
    },

    async importChatAssignments() {
      this.importing = true;
      try {
        const response = await fetch("/api/import-chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(this.importData),
        });

        if (response.ok) {
          const result = await response.json();
          alert(`Successfully imported ${result.count} assignments!`);
          // Update the selected date to show the imported data
          this.selectedDate = this.importData.duty_date;
          await this.loadData();
          this.showImportModal = false;
        } else {
          const error = await response.json();
          alert("Failed to import assignments: " + error.detail);
        }
      } catch (error) {
        alert("Failed to import assignments: " + error.message);
      } finally {
        this.importing = false;
      }
    },

    async recalculateFairness() {
      this.recalculating = true;
      try {
        const response = await fetch("/api/recalculate-fairness", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (response.ok) {
          const result = await response.json();
          alert(
            result.message || "Fairness tracking recalculated successfully!"
          );
          await this.loadData(); // Refresh all data
        } else {
          const error = await response.json();
          alert("Failed to recalculate fairness: " + error.detail);
        }
      } catch (error) {
        alert("Failed to recalculate fairness: " + error.message);
      } finally {
        this.recalculating = false;
      }
    },

    async openPersonnelModal(personId) {
      this.showPersonnelModal = true;
      this.personnelDetails = null; // Clear previous data

      try {
        const response = await fetch(`/api/personnel/${personId}/details`);
        if (response.ok) {
          this.personnelDetails = await response.json();
        } else {
          const error = await response.json();
          alert("Failed to load personnel details: " + error.detail);
          this.showPersonnelModal = false;
        }
      } catch (error) {
        alert("Failed to load personnel details: " + error.message);
        this.showPersonnelModal = false;
      }
    },

    getPostTypeClass(postTypeName) {
      const classes = {
        SOG: "post-sog",
        CQ: "post-cq",
        ECP: "post-ecp",
        VCP: "post-vcp",
        ROVER: "post-rover",
        "Stand by": "post-standby",
      };
      return (
        classes[postTypeName] ||
        "bg-gray-500 text-white px-3 py-1 rounded-full text-sm font-bold"
      );
    },

    getStatusClass(status) {
      const classes = {
        assigned: "status-assigned",
        completed: "status-completed",
        "no-show": "status-no-show",
      };
      return classes[status] || "status-assigned";
    },

    getFairnessClass(score) {
      if (score <= 5) return "fairness-low";
      if (score <= 15) return "fairness-medium";
      return "fairness-high";
    },

    formatNumber(value, decimals = 1) {
      if (typeof value === "number") {
        return value.toFixed(decimals);
      }
      return parseFloat(value || 0).toFixed(decimals);
    },

    formatDate(dateString) {
      if (!dateString) return "N/A";
      const date = new Date(dateString);
      return date.toLocaleDateString("en-US", {
        weekday: "short",
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    },

    formatTime(timeString) {
      if (!timeString) return "N/A";
      return timeString;
    },

    getSuggestedPersonnel() {
      // Return personnel sorted by fairness (lowest score first)
      return this.personnel
        .filter((p) => {
          const stats = this.fairnessStats.find((fs) => fs.person_id === p.id);
          return stats;
        })
        .sort((a, b) => {
          const aStats = this.fairnessStats.find((fs) => fs.person_id === a.id);
          const bStats = this.fairnessStats.find((fs) => fs.person_id === b.id);
          return (aStats?.fairness_score || 0) - (bStats?.fairness_score || 0);
        });
    },

    getEquipmentList(equipmentJson) {
      try {
        return JSON.parse(equipmentJson || "[]");
      } catch {
        return [];
      }
    },
  };
}

// Personnel management component
function personnelData() {
  return {
    personnel: [],
    showAddModal: false,
    newPerson: {
      rank: "",
      name: "",
      is_active: true,
    },
    ranks: ["PV2", "PFC", "SPC", "CPL", "SGT", "SSG", "SFC", "MSG", "SGM"],

    async init() {
      await this.loadPersonnel();
    },

    async loadPersonnel() {
      try {
        const response = await fetch("/api/personnel");
        this.personnel = await response.json();
      } catch (error) {
        console.error("Failed to load personnel:", error);
      }
    },

    openAddModal() {
      this.newPerson = {
        rank: "",
        name: "",
        is_active: true,
      };
      this.showAddModal = true;
    },

    async addPerson() {
      try {
        const response = await fetch("/api/personnel", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(this.newPerson),
        });

        if (response.ok) {
          await this.loadPersonnel();
          this.showAddModal = false;
        } else {
          const error = await response.json();
          alert("Failed to add person: " + error.detail);
        }
      } catch (error) {
        alert("Failed to add person: " + error.message);
      }
    },
  };
}
